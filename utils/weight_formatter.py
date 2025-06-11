"""
Weight formatting utilities for displaying large fish weights in readable units.
"""

def format_weight(weight_kg: float) -> str:
    """
    Format weight in kg to a more readable unit.
    
    Args:
        weight_kg: Weight in kilograms
        
    Returns:
        Formatted weight string with appropriate unit
    """
    # Define unit thresholds and names
    units = [
        (1e24, "Yt", "yottatons"),          # 1e24 kg (fictional, for fun)
        (1e21, "Zt", "zettatons"),          # 1e21 kg (fictional, for fun)
        (1e18, "Et", "exatons"),            # 1e18 kg (fictional, for fun)
        (1e15, "Pt", "petatons"),           # 1e15 kg (fictional, for fun)
        (1e12, "Tt", "teratons"),           # 1e12 kg (fictional, for fun)
        (1e9, "Gt", "gigatons"),            # 1e9 kg
        (1e6, "Mt", "megatons"),            # 1e6 kg
        (1e3, "ton", "tons"),                 # 1e3 kg (metric ton)
        (1, "kg", "kilograms"),             # 1 kg
        (1e-3, "g", "grams"),               # 1e-3 kg
        (1e-6, "mg", "milligrams"),         # 1e-6 kg
        (1e-9, "μg", "micrograms"),         # 1e-9 kg
        (1e-12, "ng", "nanograms"),         # 1e-12 kg
        (1e-15, "pg", "picograms"),         # 1e-15 kg
        (1e-18, "fg", "femtograms"),        # 1e-18 kg
        (1e-21, "ag", "attograms"),         # 1e-21 kg
        (1e-24, "zg", "zeptograms"),        # 1e-24 kg
        (1e-27, "yg", "yoctograms"),        # 1e-27 kg
        (1e-30, "rg", "rontograms"),        # 1e-30 kg
        (1e-33, "qg", "quectograms"),       # 1e-33 kg
        # Below this, units are not officially defined, so we invent some
        (1e-36, "xg", "xenograms"),         # 1e-36 kg (fictional)
        (1e-39, "wg", "wegdograms"),        # 1e-39 kg (fictional)
        (1e-42, "vg", "vendograms"),        # 1e-42 kg (fictional)
        (1e-45, "ug", "udecograms"),        # 1e-45 kg (fictional)
    ]
    
    # Handle zero weight
    if weight_kg == 0:
        return "0 kg"
    
    # Handle negative weights (just in case)
    if weight_kg < 0:
        return f"-{format_weight(abs(weight_kg))}"
    
    # Find the appropriate unit
    for threshold, unit, full_name in units:
        if weight_kg >= threshold:
            value = weight_kg / threshold
            
            # Format the number based on its magnitude
            if value >= 1000:
                # For very large numbers, use scientific notation
                return f"{value:.2e} {unit}"
            elif value >= 100:
                # For hundreds, show no decimal places
                return f"{value:.0f} {unit}"
            elif value >= 10:
                # For tens, show one decimal place
                return f"{value:.1f} {unit}"
            else:
                # For single digits, show two decimal places
                return f"{value:.2f} {unit}"
    
    # Fallback for extremely small weights
    return f"{weight_kg:.2e} kg"

def format_weight_detailed(weight_kg: float) -> str:
    """
    Format weight with both abbreviated and full unit names for extra clarity.
    
    Args:
        weight_kg: Weight in kilograms
        
    Returns:
        Formatted weight string with both short and long unit names
    """
    units = [
        (1e21, "Zt", "zettatons"),
        (1e18, "Et", "exatons"),
        (1e15, "Pt", "petatons"),
        (1e12, "Tt", "teratons"),
        (1e9, "Gt", "gigatons"),
        (1e6, "Mt", "megatons"),
        (1e3, "t", "tons"),
        (1, "kg", "kilograms"),
    ]
    
    if weight_kg == 0:
        return "0 kg"
    
    if weight_kg < 0:
        return f"-{format_weight_detailed(abs(weight_kg))}"
    
    for threshold, unit, full_name in units:
        if weight_kg >= threshold:
            value = weight_kg / threshold
            
            if value >= 1000:
                return f"{value:.2e} {unit} ({full_name})"
            elif value >= 100:
                return f"{value:.0f} {unit} ({full_name})"
            elif value >= 10:
                return f"{value:.1f} {unit} ({full_name})"
            else:
                return f"{value:.2f} {unit} ({full_name})"
    
    # For very small weights, just use kg
    return f"{weight_kg:.2f} kg"

# Test function to verify the formatting works correctly
if __name__ == "__main__":
    test_weights = [
        0,
        0.001,
        0.5,
        1,
        50,
        1000,
        50000,
        1000000,
        1500000000,
        1666747938381121.00,
        1e15,
        1e18,
        1e21,
    ]
    
    print("Weight Formatting Tests:")
    print("-" * 50)
    for weight in test_weights:
        formatted = format_weight(weight)
        print(f"{weight:>20.2f} kg -> {formatted}")
