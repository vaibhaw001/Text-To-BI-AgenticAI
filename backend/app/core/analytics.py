import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Tuple, Optional
from sklearn.tree import DecisionTreeRegressor, _tree
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.data import DataModel

logger = logging.getLogger("text-to-bi-backend.analytics")

def merge_data_model(data_model: DataModel) -> pd.DataFrame:
    """
    Programmatically merges all tables in a DataModel into a single unified DataFrame
    to perform multi-table correlation and regression analysis.
    """
    tables = list(data_model.tables.keys())
    if len(tables) == 0:
        return pd.DataFrame()
    if len(tables) == 1:
        return data_model.tables[tables[0]].copy()
    
    # Start with the largest table by columns/rows, or the first table (usually the fact table)
    main_df = data_model.tables[tables[0]].copy()
    merged_tables = {tables[0]}
    
    attempts = 0
    max_attempts = len(tables) * 2
    while len(merged_tables) < len(tables) and attempts < max_attempts:
        attempts += 1
        for tbl_name in tables:
            if tbl_name in merged_tables:
                continue
                
            join_keys_target = data_model.relationships.get(tbl_name, [])
            merged_with_relation = None
            join_key_source = None
            join_key_target_selected = None
            
            # Search relationships mapping to find a path to join tbl_name with already merged tables
            for m_tbl in merged_tables:
                m_keys = data_model.relationships.get(m_tbl, [])
                for k_target in join_keys_target:
                    # Case 1: Matching column name in both tables' keys
                    if k_target in m_keys and k_target in main_df.columns and k_target in data_model.tables[tbl_name].columns:
                        merged_with_relation = m_tbl
                        join_key_source = k_target
                        join_key_target_selected = k_target
                        break
                    
                    # Case 2: Substring key match (e.g. Products.id -> Sales.product_id)
                    for k_source in m_keys:
                        if k_source in main_df.columns and k_target in data_model.tables[tbl_name].columns:
                            if (k_target.lower() == 'id' and tbl_name.lower() in k_source.lower()) or \
                               (k_source.lower() == 'id' and m_tbl.lower() in k_target.lower()):
                                merged_with_relation = m_tbl
                                join_key_source = k_source
                                join_key_target_selected = k_target
                                break
                    if merged_with_relation:
                        break
                if merged_with_relation:
                    break
            
            # Fallback: Merge on any identical columns if no explicit relationship matches
            if not merged_with_relation:
                tbl_cols = set(data_model.tables[tbl_name].columns)
                main_cols = set(main_df.columns)
                common_cols = tbl_cols.intersection(main_cols)
                ignored_cols = {'date', 'name', 'description', 'status', 'id', 'index', 'sales', 'revenue', 'quantity', 'amount'}
                clean_common = [c for c in common_cols if c.lower() not in ignored_cols]
                if clean_common:
                    join_key_source = clean_common[0]
                    join_key_target_selected = clean_common[0]
                    merged_with_relation = "common_column"
                    
            if merged_with_relation:
                target_df = data_model.tables[tbl_name]
                logger.info(f"Merging '{tbl_name}' on main_df.{join_key_source} == {tbl_name}.{join_key_target_selected}")
                if join_key_source == join_key_target_selected:
                    main_df = pd.merge(main_df, target_df, on=join_key_source, how='inner')
                else:
                    main_df = pd.merge(main_df, target_df, left_on=join_key_source, right_on=join_key_target_selected, how='inner')
                merged_tables.add(tbl_name)
                break
                
    return main_df

def perform_change_attribution(
    df: pd.DataFrame, 
    target_col: str, 
    target_val: Any, 
    comparison_val: Any, 
    metric_col: str
) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    Compares metric_col sums in target_val group vs comparison_val group,
    and attributes the change to categories in other columns.
    (e.g., Laptop category explains 64% of the Sales growth between Q1 and Q2).
    """
    # Force convert to string comparisons if needed
    df_temp = df.copy()
    df_temp[target_col] = df_temp[target_col].astype(str)
    t_val_str = str(target_val)
    c_val_str = str(comparison_val)
    
    group_comp = df_temp[df_temp[target_col] == c_val_str]
    group_target = df_temp[df_temp[target_col] == t_val_str]
    
    val_comp = float(group_comp[metric_col].sum())
    val_target = float(group_target[metric_col].sum())
    total_change = val_target - val_comp
    
    if total_change == 0 or len(group_comp) == 0 or len(group_target) == 0:
        return val_comp, val_target, []
        
    drivers = []
    
    # Identify candidate columns for attribution (low cardinality categorical columns)
    candidate_cols = []
    for col in df_temp.columns:
        if col in [target_col, metric_col]:
            continue
        # Skip ID/Key columns
        col_lower = col.lower()
        if col_lower.endswith('id') or col_lower.endswith('key') or col_lower == 'index':
            continue
        # Only check categorical/string columns with reasonable cardinality
        if df_temp[col].dtype == 'object' or df_temp[col].dtype.name == 'category':
            if df_temp[col].nunique() <= 30:
                candidate_cols.append(col)
                
    for col in candidate_cols:
        # Group by and calculate sums for both groups
        comp_sums = group_comp.groupby(col)[metric_col].sum().to_dict()
        target_sums = group_target.groupby(col)[metric_col].sum().to_dict()
        
        all_cats = set(comp_sums.keys()).union(set(target_sums.keys()))
        for cat in all_cats:
            s_comp = comp_sums.get(cat, 0.0)
            s_target = target_sums.get(cat, 0.0)
            cat_change = s_target - s_comp
            
            # If cat_change moves in the same direction as total_change, it's a driver
            pct_contrib = (cat_change / total_change) * 100.0 if total_change != 0 else 0.0
            
            drivers.append({
                "factor": f"{col}: {cat}",
                "metric_comp": s_comp,
                "metric_target": s_target,
                "absolute_change": cat_change,
                "percentage": round(pct_contrib, 1),
                "type": "increase" if cat_change > 0 else "decrease"
            })
            
    # Sort drivers by absolute change contribution
    drivers.sort(key=lambda x: abs(x['absolute_change']), reverse=True)
    return val_comp, val_target, drivers[:8]

def perform_key_influencers(
    df: pd.DataFrame,
    target_col: str,
    target_val: Any,
    metric_col: str
) -> List[Dict[str, Any]]:
    """
    Fits a DecisionTreeRegressor to predict metric_col on the dataset (or on target segment)
    and extracts top correlation statistics to explain what drives metric_col.
    """
    df_clean = df.copy()
    
    # Fill missing values
    for col in df_clean.columns:
        if df_clean[col].dtype in ['float64', 'int64']:
            df_clean[col] = df_clean[col].fillna(df_clean[col].median() if not df_clean[col].isna().all() else 0)
        else:
            df_clean[col] = df_clean[col].fillna("Unknown")
            
    # Baseline global average of the metric
    baseline_mean = float(df_clean[metric_col].mean()) if len(df_clean) > 0 else 0.0
    
    # Filter dataset to target segment if explaining segment specific drivers (e.g. Region == 'West')
    is_segment_analysis = target_col in df_clean.columns and target_val is not None
    if is_segment_analysis:
        df_clean[target_col] = df_clean[target_col].astype(str)
        t_val_str = str(target_val)
        df_analysis = df_clean[df_clean[target_col] == t_val_str].copy()
    else:
        df_analysis = df_clean.copy()
        
    if len(df_analysis) < 2:
        # Not enough data at all
        return []
        
    drivers = []
    
    # 1. Statistical check: category average impact compared to global baseline
    candidate_cols = []
    for col in df_analysis.columns:
        if col in [target_col, metric_col]:
            continue
        col_lower = col.lower()
        if col_lower.endswith('id') or col_lower.endswith('key') or col_lower == 'index' or col_lower.startswith('date'):
            continue
        if df_analysis[col].dtype == 'object' or df_analysis[col].dtype.name == 'category':
            if df_analysis[col].nunique() <= 30:
                candidate_cols.append(col)
                
    min_count = max(1, min(3, len(df_analysis) // 3))
    for col in candidate_cols:
        cat_averages = df_analysis.groupby(col)[metric_col].agg(['mean', 'count'])
        for cat, row in cat_averages.iterrows():
            if row['count'] >= min_count:
                avg_val = float(row['mean'])
                diff = avg_val - baseline_mean
                ratio = avg_val / baseline_mean if baseline_mean > 0 else 1.0
                
                # Check absolute ratio difference (impact >= 10%)
                if abs(ratio - 1.0) >= 0.10:
                    drivers.append({
                        "factor": f"{col}: {cat}",
                        "impact": f"Average {metric_col} is {avg_val:.2f} ({ratio:.1f}x baseline average of {baseline_mean:.2f})",
                        "score": abs(diff) * (row['count'] / len(df_analysis)),
                        "percentage": round((ratio - 1.0) * 100.0, 1),
                        "type": "increase" if diff > 0 else "decrease"
                    })

    # 2. Decision Tree Rules extraction (only if enough samples exist, e.g., >= 5)
    if len(df_analysis) >= 5:
        try:
            features_cat = []
            features_num = []
            for col in df_analysis.columns:
                if col in [target_col, metric_col]:
                    continue
                col_lower = col.lower()
                if col_lower.endswith('id') or col_lower.endswith('key') or col_lower == 'index' or col_lower.startswith('date'):
                    continue
                if df_analysis[col].dtype in ['float64', 'int64']:
                    features_num.append(col)
                elif col in candidate_cols:
                    features_cat.append(col)
                    
            if len(features_cat) > 0 or len(features_num) > 0:
                X_data = df_analysis[features_num].copy()
                if len(features_cat) > 0:
                    X_cat_dummies = pd.get_dummies(df_analysis[features_cat], drop_first=False)
                    X_data = pd.concat([X_data, X_cat_dummies], axis=1)
                    
                y_data = df_analysis[metric_col]
                
                # Train decision tree
                min_leaf_samples = max(2, min(5, len(df_analysis) // 3))
                dt = DecisionTreeRegressor(max_depth=3, min_samples_leaf=min_leaf_samples)
                dt.fit(X_data, y_data)
                
                # Traverse tree
                tree_ = dt.tree_
                feature_names = list(X_data.columns)
                feature_name = [feature_names[i] if i != _tree.TREE_UNDEFINED else "undefined" for i in tree_.feature]
                
                def recurse(node, rule_accum):
                    if tree_.feature[node] != _tree.TREE_UNDEFINED:
                        name = feature_name[node]
                        threshold = tree_.threshold[node]
                        
                        clean_name = name
                        for cat_col in features_cat:
                            if name.startswith(cat_col + "_"):
                                clean_name = f"{cat_col}: {name[len(cat_col)+1:]}"
                                break
                                
                        recurse(tree_.children_right[node], rule_accum + [f"{clean_name} is present/high"])
                        recurse(tree_.children_left[node], rule_accum + [f"{clean_name} is absent/low"])
                    else:
                        leaf_mean = float(tree_.value[node][0][0])
                        samples = int(tree_.n_node_samples[node])
                        ratio = leaf_mean / baseline_mean if baseline_mean > 0 else 1.0
                        
                        if samples >= min_leaf_samples and abs(ratio - 1.0) >= 0.15:
                            rules_text = " AND ".join(rule_accum)
                            drivers.append({
                                "factor": f"Combination ({samples} rows)",
                                "impact": f"When {rules_text}, average {metric_col} is {leaf_mean:.2f} ({ratio:.1f}x baseline)",
                                "score": abs(leaf_mean - baseline_mean) * (samples / len(df_analysis)),
                                "percentage": round((ratio - 1.0) * 100.0, 1),
                                "type": "increase" if leaf_mean > baseline_mean else "decrease"
                            })
                            
                recurse(0, [])
        except Exception as e:
            logger.error(f"Failed to fit decision tree or extract rules: {str(e)}")
        
    # Remove duplicates and clean list
    seen_factors = set()
    unique_drivers = []
    for d in drivers:
        if d['factor'] not in seen_factors:
            seen_factors.add(d['factor'])
            unique_drivers.append(d)
            
    # Sort drivers by score or percentage impact
    unique_drivers.sort(key=lambda x: abs(x.get('percentage', 0)), reverse=True)
    return unique_drivers[:6]

def generate_analytics_summary(
    metric_col: str,
    target_col: str,
    target_val: Any,
    comparison_val: Optional[Any],
    question: Optional[str],
    baseline_stats: Dict[str, Any],
    drivers: List[Dict[str, Any]],
    llm: Any
) -> str:
    """
    Constructs a detailed prompt with statistical findings and runs it through the LLM
    to generate a polished 3-4 sentence executive summary.
    """
    if comparison_val is not None:
        analysis_context = f"""
We are comparing the total of '{metric_col}' across two values of '{target_col}':
- Reference/Comparison Group: '{comparison_val}' (Total: {baseline_stats['comp_total']:.2f})
- Target Group: '{target_val}' (Total: {baseline_stats['target_total']:.2f})
- Total Net Change: {baseline_stats['net_change']:.2f} ({baseline_stats['pct_change']:.1f}% change)

Our statistical change-attribution analysis identified the following primary drivers:
"""
        for d in drivers:
            analysis_context += f"- Factor '{d['factor']}' contributed {d['percentage']}% ({d['absolute_change']:.2f} absolute) to the total change. (Type: {d['type']})\n"
            
    else:
        analysis_context = f"""
We are analyzing what drives '{metric_col}' in the segment '{target_col} == {target_val}'.
The global baseline average of '{metric_col}' across the entire dataset is {baseline_stats['baseline_avg']:.2f}.
Inside this segment (or dataset), our machine learning decision tree and correlation analysis identified the following key influencers:
"""
        for d in drivers:
            analysis_context += f"- Factor '{d['factor']}': {d['impact']}. (Percentage Shift: {d['percentage']}%, Type: {d['type']})\n"

    system_prompt = "You are a senior executive BI analyst. Your goal is to write a concise, professional, and factual executive summary of a data analysis."
    
    human_prompt = f"""
{analysis_context}

User's Question:
"{question or f'What drives {metric_col} in {target_col} {target_val}?'}"

Based on the statistical drivers listed above, write a concise, high-level executive summary (3-4 sentences max). 
Ensure you:
1. State the main finding clearly with exact numbers (totals, percentages, or ratios).
2. Explicitly highlight the top correlated factor(s) (e.g. "Category: Laptop represents 64% of the growth in this quarter" or "Corporate segment drives a 2.5x increase in sales").
3. Keep the tone highly professional, objective, and analytical. Avoid generic introductory filler.
"""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        response = llm.invoke(messages)
        summary = response.content.strip()
        # Strip markdown wrapper if any
        if summary.startswith("```"):
            summary = summary.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
        return summary
    except Exception as e:
        logger.error(f"Error generating summary via LLM: {str(e)}")
        return f"Statistical analysis complete. Top driver identified: {drivers[0]['factor'] if drivers else 'None'}."
