def normalize_errors(errors):
    """Iterative version - slightly faster"""
    normalized = []
    stack = [(errors, '')]
    
    while stack:
        current, parent_key = stack.pop()
        
        if not isinstance(current, dict):
            continue
            
        for key, value in current.items():
            field_name = 'general' if key == 'non_field_errors' else (
                f"{parent_key}.{key}" if parent_key else key
            )
            
            if isinstance(value, dict):
                stack.append((value, field_name))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        stack.append((item, field_name))
                    else:
                        normalized.append({
                            'field': field_name,
                            'message': str(item)
                        })
    
    return normalized