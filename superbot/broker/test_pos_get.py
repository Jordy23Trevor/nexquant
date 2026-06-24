import MetaTrader5 as mt5

def test():
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return
        
    symbol = "USDCAD"
    pos_by_sym = mt5.positions_get(symbol=symbol)
    print(f"positions_get(symbol='{symbol}') returned: {pos_by_sym}")
    
    all_pos = mt5.positions_get()
    print(f"positions_get() returned {len(all_pos) if all_pos else 0} positions.")
    
    mt5.shutdown()

if __name__ == "__main__":
    test()
