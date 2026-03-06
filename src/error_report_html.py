"""HTML error report generator."""
from typing import List, Dict
from error_report import (
    ErrorType,
    categorize_errors,
)


def write_error_report_html(errors: List[str], tasks: List[dict], output_file: str) -> None:
    """
    Write validation errors to a beautiful HTML report file.
    
    Args:
        errors: List of error strings from validate_report()
        tasks: List of task dicts with 'id' and 'title' keys
        output_file: Path to output HTML file
    """
    categorized = categorize_errors(errors)
    error_types = list(ErrorType)
    task_ids = [str(t.get("id", "")) for t in tasks]
    task_map = {str(t.get("id", "")): t.get("title", "") for t in tasks}
    
    total_errors = len(errors)
    affected_tasks = len(categorized)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Error Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .stats {{
            display: flex;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .stat {{
            background: rgba(255, 255, 255, 0.2);
            padding: 15px 25px;
            border-radius: 5px;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #fff;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        section {{
            background: white;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        section h2 {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 2px solid #e9ecef;
            font-size: 1.5em;
            color: #333;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        
        th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #dee2e6;
            color: #495057;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .checkmark {{
            color: #28a745;
            font-weight: bold;
            font-size: 1.2em;
        }}
        
        .x-mark {{
            color: #dc3545;
            font-weight: bold;
            font-size: 1.2em;
        }}
        
        .task-name {{
            font-weight: 600;
            color: #667eea;
        }}
        
        .error-list {{
            padding: 20px;
        }}
        
        .task-section {{
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        
        .task-section h3 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.1em;
        }}
        
        .error-type {{
            margin: 15px 0;
            padding-left: 20px;
        }}
        
        .error-type strong {{
            color: #764ba2;
            display: block;
            margin-bottom: 8px;
        }}
        
        .error-message {{
            background: white;
            padding: 8px 12px;
            margin: 5px 0;
            border-left: 3px solid #dc3545;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            color: #555;
            word-break: break-word;
        }}
        
        .no-errors {{
            padding: 40px;
            text-align: center;
            color: #28a745;
            font-size: 1.2em;
        }}
        
        footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📋 Validation Error Report</h1>
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{total_errors}</div>
                    <div class="stat-label">Total Errors</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{affected_tasks}/{len(task_ids)}</div>
                    <div class="stat-label">Affected Tasks</div>
                </div>
            </div>
        </header>
        
        <section>
            <h2>Error Overview Table</h2>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Task ID</th>
                            <th>Task Title</th>
                            {"".join(f'<th>{et.value}</th>' for et in error_types)}
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for task in tasks:
        task_id = str(task.get("id", ""))
        task_title = task.get("title", "")
        html_content += f"                        <tr>\n"
        html_content += f"                            <td><strong>{task_id}</strong></td>\n"
        html_content += f"                            <td class='task-name'>{task_title}</td>\n"
        
        for error_type in error_types:
            if task_id in categorized:
                errors_for_type = [
                    te for te in categorized[task_id]
                    if te.error_type == error_type
                ]
                if errors_for_type:
                    html_content += f"                            <td class='x-mark'>✗</td>\n"
                else:
                    html_content += f"                            <td class='checkmark'>✓</td>\n"
            else:
                html_content += f"                            <td class='checkmark'>✓</td>\n"
        
        html_content += f"                        </tr>\n"
    
    html_content += """                    </tbody>
                </table>
            </div>
        </section>
"""
    
    if categorized:
        html_content += """        <section>
            <h2>Detailed Error Summary</h2>
            <div class="error-list">
"""
        
        for task_id in task_ids:
            if task_id in categorized:
                task_title = task_map.get(task_id, "")
                task_errs = categorized[task_id]
                
                html_content += f"""                <div class="task-section">
                    <h3>Task {task_id}: {task_title}</h3>
                    <p><strong>{len(task_errs)} error(s)</strong></p>
"""
                
                by_type: Dict[ErrorType, List[str]] = {}
                for te in task_errs:
                    if te.error_type not in by_type:
                        by_type[te.error_type] = []
                    by_type[te.error_type].append(te.message)
                
                for error_type, msgs in by_type.items():
                    html_content += f'                    <div class="error-type">\n'
                    html_content += f'                        <strong>• {error_type.value}</strong>\n'
                    for msg in msgs:
                        html_content += f'                        <div class="error-message">{msg}</div>\n'
                    html_content += f'                    </div>\n'
                
                html_content += f"""                </div>
"""
        
        html_content += """            </div>
        </section>
"""
    else:
        html_content += """        <section>
            <div class="no-errors">✓ No errors found!</div>
        </section>
"""
    
    html_content += """        <footer>
            <p>Generated automatically by es-report-tools validation system</p>
        </footer>
    </div>
</body>
</html>
"""
    
    with open(output_file, "w") as f:
        f.write(html_content)
