from typing import Union, Tuple

def parse_amount(amount_str: str, balance: int, max_amount: int = None, context: str = "wallet") -> Tuple[Union[int, None], str]:
    """
    Parse amount from various formats for economy commands
    Returns (amount, error_message)
    
    Supports:
    - Regular numbers: 100, 400, 1000
    - Percentages: 50%, 100%, 5.5%
    - K/M notation: 1k, 1.5k, 100k, 1m, 2.5m
    - Scientific notation: 1e3, 1.5e3, 1e6
    - Special keywords: all, max, half
    
    Args:
        amount_str: The string to parse
        balance: The user's available balance 
        max_amount: Optional maximum allowed amount (e.g., bank space)
        context: Context for error messages ("wallet", "bank", etc.)
    """
    try:
        # Clean the input
        amount_str = amount_str.lower().strip()
        
        # Handle special keywords
        if amount_str in ['all', 'max']:
            return min(balance, max_amount) if max_amount is not None else balance, None
        elif amount_str in ['half', '1/2']:
            amount = balance // 2
            return min(amount, max_amount) if max_amount is not None else amount, None
            
        # Handle percentage
        if amount_str.endswith('%'):
            try:
                percentage = float(amount_str[:-1])
                if not 0 < percentage <= 100:
                    return None, "Percentage must be between 0 and 100!"
                amount = int((percentage / 100) * balance)
                return min(amount, max_amount) if max_amount is not None else amount, None
            except ValueError:
                return None, "Invalid percentage format!"
        
        # Handle k/m notation and scientific notation
        multiplier = 1
        if amount_str.endswith('k'):
            multiplier = 1000
            amount_str = amount_str[:-1]
        elif amount_str.endswith('m'):
            multiplier = 1000000
            amount_str = amount_str[:-1]
        
        # Convert scientific notation and decimals
        if 'e' in amount_str:
            amount = float(amount_str)
        else:
            amount = float(amount_str)
        
        # Apply multiplier and round
        final_amount = round(amount * multiplier)
        
        if final_amount <= 0:
            return None, "Amount must be positive!"
            
        return final_amount, None
        
    except ValueError:
        return None, "Invalid amount format!"

def get_amount_help_text(command_name: str, balance_type: str = "wallet") -> str:
    """
    Get help text for amount parsing formats
    
    Args:
        command_name: Name of the command (e.g., "pay", "deposit")
        balance_type: Type of balance ("wallet", "bank", etc.)
    """
    return f"""**{command_name.title()} Amount Guide**

**Usage:**
`.{command_name} <amount>`
`.{command_name} 50%` - Use 50% of {balance_type}
`.{command_name} all` - Use maximum amount
`.{command_name} half` - Use half of {balance_type}
`.{command_name} 1k` - Use 1,000
`.{command_name} 1.5m` - Use 1,500,000
`.{command_name} 1e3` - Use 1,000 (scientific notation)
`.{command_name} 2.5e5` - Use 250,000 (scientific notation)"""
