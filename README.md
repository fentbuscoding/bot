# South Bronx Bot
> Gambling on steroids, with an economy in its sidehand, fishing around its waist, and a stock market to tie it all together.

South Bronx bot adds a layer of irony to your server other bots fail to bring to the table, it was literally made because the gambling addiction in /furryporn was so bad we made a bot for it, then other servers wanted it, then we came here.

# __What Makes It Different?__
It's mainly written by one dude, but with all the [contributors on github](https://github.com/bronxbot/bot) (thank you all so much) it's mainly by the people for the people.. But mainly its not for profit, there isn't any premium or cash grab, we do it all for free. For the love of gambling ❤️

# BronxBots Features

# Accepted Variables
***Most*** commands that use economic values also accept these:
`1k = 1000`
`2.5% = 2.5 percentage of balance or wallet where applicable`
`2e5 = 200000 scientific notation`

# Help
`.h`, `.help`
> sends a modal with buttons that allow you to view every command by category

`.invite`, `.support`
>  get an invite to the BronxBot [support server](https://discord.gg/jvyYWkj3ts)

# AutoFishing
`.auto`
> opens the initial modal for autofishing
> *the autofisher modal also has buttons to quickly use these commands!*

`.auto buy`
> buy an autofisher

`.auto upgrade`
> upgrade the efficiency of your autofishers

`.auto deposit <amount>`
> deposit bronkbuks into your autofishing balance

# Bazaar
> The bazaar is a marketplace / stock market hybrid that gets its price from its visitors
**How it works:**
```python
visitor_factor = len(self.visitors) * 0.5
spending_factor = math.log10(max(1, self.total_spent)) * 10
        
price = self.stock_base_price + visitor_factor + spending_factor
        
# Add some randomness
price *= random.uniform(0.9, 1.1)
```
> - a snippet from the [bazzar.py cog](https://github.com/bronxbot/bot/blob/main/cogs/economy/Bazaar.py) 

`.bazaar`
> View the possible items the bazaar has to offer, buy some stock, or buy some items 
> *There are buttons on this command to quickly do some of the commands below*

`.bazaar-buy <item_id> [amount=1]`
> buy an item from the bazaars shop 

`.bazaar-stock [amount=1]`
> buy bazaar stock

`.secret-bazaar`
> for the prestigious.

`.secret-buy <item_id>`
> for the prestigious to shop.

# Cypher
> I got bored and coded a cyphering thing for e2e conversations through discord bots, its doable?

`.cypher_test [key] [test]`
> runs a decryption and encryption test on a shring

`.cypher [key] [text]`
> **RECOMMENDED** run with no arguments to start a private cypher in DMs

`.decypher [key] [text]`
> **RECOMMENDED** run with no arguments to start a private cypher in DMs

# Economy
> The heart and soul of BronxBot lives here, this isn't quite Kansas yet (gambling), but its what makes the bot go. So let's not take it for granted.

`.balance [member]`
> check your (or a members) wallet, bank & net-worth!

`.bankupgrade`, `.bu`
> purchase a bankupgrade to increase your bank limit

`.beg`
> beg someone for money

`.work`
> work for some easy cash

`.daily`
> get your daily dose of stimulus money

`.pay [member] [amount]`
> pay someone money

`.deposit [amount]`, `.d`, `.dep`
> deposit money into your bank account
> `.deposit all`
> `.deposit 50%`
> `.deposit 3e5`
> `.deposit 1000`

`.withdraw [amount]`, `.w`, `.with`
> withdraw money from your bank account
> `.withdraw all`
> `.withdraw 50%`
> `.withdraw 3e5`
> `.withdraw 1000`

`.leaderboard [scope=server/global]`,`.lb`
> show the leaderboard (or global leaderboard by using `.leaderboard global`)

`.rob [victim]`
> rob somebody


# Gambling
> The moment you're all waiting for.

`.blackjack <bet>`,`.bj`
> play a game of blackjack against the bot

`.bomb [channel]`
> start a money bomb in a channel
>
> bombs are time dynamic based on the amount of money spent on a bomb
> 
> anyone who talks in a channel the bomb is currently in has a 50% chance of exploding (the bot will react) and the user will get a random amount of money

`.coinflip <bet> [choice]`
> heads or tails

`.crash <bet> `
> that one game adin ross plays on stream but ported to discord

`.doubleornothing [items]`
> coinflip for items

`.roulette [bet] [choice]`
> play a game of roulette
> 
> **betting guide**
> > number (0-36) - **35:1 payout**
> > red/black - 2:1 payout
> > even/odd - 2:1 payout
> > green(0) - **35:1 payout**
> 
> **usage guide**
> > .rlt 500 red *(bet 500 on red)*
> > .rlt all 7 *(put everything on lucky number 7)*
> > .rlt half odd *(put half your balance on odd)*

`.slots <bet>`
> Play the slots
> 
> Under the hood, a snippet from [line 24-32](https://github.com/bronxbot/bot/blob/main/cogs/economy/Gambling.py)
```python
self.slot_symbols = [
            ("🍒", 30),
            ("🍋", 25),
            ("🍊", 20),
            ("🍇", 15),
            ("🔔", 7),
            ("7️⃣", 3),
            ("💎", 1)
        ]
```
> - these are the weights of the slot machine, feels rigged right? well its not, because we tell you these are the odds.

# Interest
> works by using a base percentage which you can upgrade through a command which eventually requires an item to upgrade

`.interest`, `.i`
> claim your daily interest from your bank

`.interest_upgrade`,`.iu`
> upgrade interest level

`.interest_info`,`.ii`
> get info on your interest rate, among other things..

# Fishing
`.fish`,`.fs`
> go fishing

`.fishinv`, `.finv`
> view the catches 

`.sellfish [fish_id=all]`,`.sf`
> *Fish Ids = Rarities*
> **supported ids:**
> - normal
> - rare
> - event
> - mutated
> - all
> sell your fish based on `id`

# Fun
> Literally slop commands, these just do random things and don't belong anywhere

`.ascii <name>`
> Sends ascii art
> *cat, dog, heart, star, shrug, tableflip*

`.8ball [question]`
> ask the almighty 8ball

`.cooldown`
> check command cooldowns

`.guess [max_num=100]`
> starts a higher or lower number guessing game that picks a number in between 1 & max_num

`.hack [user]`
> totally real hacking simulator

`.lovecalc <user1> <user2>`, `.ship`
> very real love calculator aswell

`.pick [item1] [item2] [item3] ...`
> pick a random option from a list
> for people who are indecisive￼, this is your best friend

`.roll [dice=1d6]`
> roll a dice
> format: 2d20 (2 separate 20 dice), 1d6 (one 6 sided dice), etc

`.typingtest [difficulty=easy]`
> do a typing test
> **difficulties:**
> - easy
> - medium
> - hard

`.fireworks`
> enjoy some e-fireworks

# Text Manipulation
> To staff, please set your filters in your default automod, we are not responsible for the **horrific output due to horrific input**
  
`.mocktext [text]`
> mOcK sOmE tExT lIkE tHiS

`.tinytext [text]`
> convert to ᵗⁱⁿʸ ˢᵘᵖᵉʳˢᶜʳⁱᵖᵗ

`.reverse [text]`
> ʇxǝʇ ruoy esreveɹ

`.owoify [text]`
> uwu-ify youw text owo *nuzzles*

`.emojify [text]`
> turn text into 🔤 regional 🔤 indicators

