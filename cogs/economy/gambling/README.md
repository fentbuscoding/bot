# Gambling Module - REBALANCED FOR ANTI-INFLATION

This directory contains the modular gambling system for the Discord bot. **MAJOR UPDATE:** All gambling games have been **HEAVILY NERFED** to combat extreme inflation where some users have 100+ billion coins.

## 🚨 CRITICAL REBALANCING CHANGES

### Progressive Bet Limits (All Games)
- **0-99k balance:** Maximum bet 10k
- **100k-499k balance:** Maximum bet 25k  
- **500k-999k balance:** Maximum bet 50k
- **1M-4.9M balance:** Maximum bet 100k
- **5M-9.9M balance:** Maximum bet 200k
- **10M+ balance:** Maximum bet 500k (HARD CAP)

### Massive Payout Nerfs

#### Coinflip
- **OLD:** 1x payout (even money)
- **NEW:** 0.9x payout (house edge increased)

#### Slots 
- **Diamond Jackpot:** 100x → **3x** (97% REDUCTION!)
- **Lucky 7s:** 20x → **2.5x** (87.5% REDUCTION!)
- **Triple Bells:** 10x → **2x** (80% REDUCTION!)
- **Other Triples:** 5x → **1.8x** (64% REDUCTION!)
- **Doubles:** 2x → **1.2x** (40% REDUCTION!)

#### Blackjack
- **Blackjack win:** 1.5x → **1.3x** (13% REDUCTION)
- **Regular win:** 1x → **0.9x** (10% REDUCTION)

#### Roulette
- **Number bets:** 35:1 → **15:1** (57% REDUCTION!)
- **Color bets:** 2:1 → **1.8:1** (10% REDUCTION)
- **Odd/even bets:** 2:1 → **1.8:1** (10% REDUCTION)
- **Green (0) bet:** 35:1 → **15:1** (57% REDUCTION!)

#### Plinko
- **Multipliers:** [0.2-10x] → **[0.1-2x]** (80%+ reduction!)
- **Max multiplier:** 10x → **2x** (80% REDUCTION!)

#### Crash
- **Crash points:** Heavily nerfed to 1.1x-2.0x range

## Module Structure

```
gambling/
├── __init__.py          # Main coordinator that loads all sub-modules
├── card_games.py        # Card-based games (Blackjack with splitting)
├── chance_games.py      # Pure chance games (Coinflip, Slots, Double or Nothing)
├── special_games.py     # Complex games (Crash, Roulette, Bomb)
└── plinko.py           # Plinko game (NEW!)
```

## Games Available

### Card Games (`card_games.py`)
- **Blackjack** (`.blackjack`, `.bj`) - Full-featured blackjack with splitting up to 4 hands, doubling, and proper dealer AI

### Chance Games (`chance_games.py`)
- **Coinflip** (`.coinflip`, `.cf`, `.flip`) - Classic heads or tails betting
- **Slots** (`.slots`) - 3-reel slot machine with weighted symbols and multiple payout tiers
- **Double or Nothing** (`.doubleornothing`, `.double`, `.don`, `.dbl`) - Risk inventory items for double rewards

### Special Games (`special_games.py`)
- **Crash** (`.crash`) - Multiplier game that can crash at any moment, with auto-cashout feature
- **Roulette** (`.roulette`, `.rlt`) - Full roulette wheel with number, color, and odd/even betting
- **Bomb** (`.bomb`) - Channel-wide money bomb that affects anyone who talks

### Plinko (`plinko.py`)
- **Plinko** (`.plinko`) - **NEW!** Classic plinko game where you drop a ball down a peg board to hit multiplier slots

## Features

### Shared Utilities
- **ToS Integration**: All games require Terms of Service acceptance
- **Bet Parsing**: Support for `all`, `half`, percentages (`50%`), and numeric amounts
- **Active Games Tracking**: Prevents multiple concurrent games per user
- **Rate Limiting**: Built-in cooldowns and message edit throttling
- **Comprehensive Logging**: Economy transactions and command usage tracking
- **Error Handling**: Robust error handling with graceful fallbacks

### Plinko Game Features
- **Visual Board**: ASCII art representation of the plinko board
- **Real-time Animation**: Watch the ball bounce through 10 rows of pegs
- **16 Multiplier Slots**: Ranging from 0.2x (lose your mortgage!) to 10x
- **Realistic Physics**: Ball bounces left/right with 50% probability at each peg
- **Suspenseful Experience**: Timed animations build tension as the ball falls

### Multiplier Distribution (Plinko)
```
0.2x | 0.5x | 1.0x | 1.5x | 2.0x | 3.0x | 5.0x | 10x | 10x | 5.0x | 3.0x | 2.0x | 1.5x | 1.0x | 0.5x | 0.2x
```

The multipliers are designed to favor lower payouts (as requested for the mortgage-losing experience), with the highest multipliers (10x) in the center being hardest to hit.

## Technical Details

### Cog Loading
The `__init__.py` file acts as a coordinator that loads all sub-cogs:
- `CardGames`
- `ChanceGames` 
- `SpecialGames`
- `Plinko`
- `Gambling` (main coordinator)

### Backward Compatibility
The original `Gambling.py` file has been replaced with a simple import wrapper to maintain compatibility with existing bot loading systems.

### Database Integration
All games integrate with the existing database system:
- Wallet balance checking and updates
- Inventory management (for Double or Nothing)
- Bank operations (for Bomb payouts)
- Transaction logging for analytics

### Rate Limiting & Anti-Abuse
- Per-user active game tracking
- Command cooldowns
- Message edit rate limiting
- Automatic cleanup of stuck games every 15 minutes

## Usage Examples

```
.plinko 1000           # Bet 1000 coins on plinko
.plinko all            # Bet entire wallet
.plinko 25%            # Bet 25% of wallet

.blackjack 5000        # Play blackjack with splitting
.crash 2000 1.5x       # Play crash with auto-cashout at 1.5x
.roulette 1000 red     # Bet on red in roulette
.bomb #general 10000   # Start a 10k money bomb in #general
```

## Notes
- All games require ToS acceptance before playing
- Games are blocked in certain channels (configurable in each module)
- Comprehensive error handling ensures games don't get stuck
- Stats logging provides analytics for bot administrators
