# Legacy gambling file - now imports from modular structure
# This file is kept for backward compatibility

# Import the new modular gambling system
from .gambling import setup

# Re-export the setup function
__all__ = ['setup']
        
        # Slot machine symbols with weights
        self.slot_symbols = [
            ("🍒", 30),
            ("🍋", 25),
            ("🍊", 20),
            ("🍇", 15),
            ("🔔", 7),
            ("7️⃣", 3),
            ("💎", 1)
        ]
        
        # Roulette numbers and colors
        self.roulette_numbers = [
            (0, "green"),
            (32, "red"), (15, "black"), (19, "red"), (4, "black"), (21, "red"), (2, "black"), 
            (25, "red"), (17, "black"), (34, "red"), (6, "black"), (27, "red"), (13, "black"), 
            (36, "red"), (11, "black"), (30, "red"), (8, "black"), (23, "red"), (10, "black"), 
            (5, "red"), (24, "black"), (16, "red"), (33, "black"), (1, "red"), (20, "black"), 
            (14, "red"), (31, "black"), (9, "red"), (22, "black"), (18, "red"), (29, "black"), 
            (7, "red"), (28, "black"), (12, "red"), (35, "black"), (3, "red"), (26, "black")
        ]
        self.blocked_channels = [1378156495144751147, 1260347806699491418]
    
    # piece de resistance: cog_check
    async def cog_check(self, ctx):
        """Global check for all commands in this cog"""
        # Check if gambling is disabled in this channel
        if ctx.channel.id in self.blocked_channels and not ctx.author.guild_permissions.administrator:
            await ctx.reply(
                random.choice([f"❌ Gambling commands are disabled in this channel. "
                f"degens, please use them in another channel.",
                "<#1314685928614264852> is a good place for that."])
            )
            return False
        
        # Check if user has accepted ToS
        if not await check_tos_acceptance(ctx.author.id):
            await prompt_tos_acceptance(ctx)
            return False
            
        return True
        return True

    @commands.command(aliases=['bj'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def blackjack(self, ctx, bet: str):
        """Play blackjack against the dealer"""
        if ctx.author.id in self.active_games:
            return await ctx.reply("❌ You already have an active game!")
            
        self.active_games.add(ctx.author.id)
        
        try:
            # Parse bet amount
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            parsed_bet = await self._parse_bet(bet, wallet)
            
            if not parsed_bet:
                self.active_games.remove(ctx.author.id)
                return await ctx.reply("❌ Invalid bet amount!")

            if parsed_bet <= 0:
                self.active_games.remove(ctx.author.id)
                return await ctx.reply("❌ Bet amount must be greater than 0!")

            if parsed_bet > wallet:
                self.active_games.remove(ctx.author.id)
                return await ctx.reply("❌ You don't have enough money for that bet!")
                
            # Initialize game
            dealer_hand = [self._draw_card(), self._draw_card()]
            player_hand = [self._draw_card(), self._draw_card()]

            print(f"Card 1: {player_hand[0]}, Card 2: {player_hand[1]}")  # Debug print
            print(f"Can split: {self._can_split(player_hand)}")  # Debug print
            # Check for blackjack
            player_bj = self._check_blackjack(player_hand)
            dealer_bj = self._check_blackjack(dealer_hand)
            
            if player_bj and dealer_bj:
                # Push - return bet
                self.stats_logger.log_command_usage("blackjack")  # Log usage
                self.active_games.remove(ctx.author.id)
                return await ctx.send(embed=self._blackjack_embed(
                    "Push! Both have Blackjack",
                    player_hand,
                    dealer_hand,
                    parsed_bet,
                    0,
                    wallet
                ))
            elif player_bj:
                # Player wins 3:2
                winnings = int(parsed_bet * 1.5)
                await db.update_wallet(ctx.author.id, winnings, ctx.guild.id)
                self.stats_logger.log_command_usage("blackjack")  # Log usage
                self.stats_logger.log_economy_transaction(ctx.author.id, "blackjack", winnings, True)  # Log win
                self.active_games.remove(ctx.author.id)
                return await ctx.send(embed=self._blackjack_embed(
                    "Blackjack! You win!",
                    player_hand,
                    dealer_hand,
                    parsed_bet,
                    winnings,
                    wallet + winnings
                ))
            elif dealer_bj:
                # Dealer wins
                await db.update_wallet(ctx.author.id, -parsed_bet, ctx.guild.id)
                self.stats_logger.log_command_usage("blackjack")  # Log usage
                self.stats_logger.log_economy_transaction(ctx.author.id, "blackjack", parsed_bet, False)  # Log loss
                self.active_games.remove(ctx.author.id)
                return await ctx.send(embed=self._blackjack_embed(
                    "Dealer has Blackjack! You lose!",
                    player_hand,
                    dealer_hand,
                    parsed_bet,
                    -parsed_bet,
                    wallet - parsed_bet
                ))
            
            # Game continues
            view = self._blackjack_view(ctx.author.id, parsed_bet, player_hand, dealer_hand, wallet)
            embed = self._blackjack_embed(
                "Your turn - Hit or Stand?",
                player_hand,
                [dealer_hand[0], "❓"],
                parsed_bet,
                0,
                wallet
            )
            
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            self.logger.error(f"Blackjack error: {e}")
            if ctx.author.id in self.active_games:
                self.active_games.remove(ctx.author.id)
            await ctx.reply("❌ An error occurred while starting the game.")

    def _can_split(self, hand: list) -> bool:
        """Check if hand can be split (two cards of same value)"""
        if len(hand) != 2:
            return False
        card1 = hand[0][:-1]  # Remove suit
        card2 = hand[1][:-1]
        return card1 == card2

    def _blackjack_view(self, user_id: int, bet: int, player_hand: list, dealer_hand: list, wallet: int, split_count: int = 0):
        """Create the blackjack game view with buttons"""
        view = discord.ui.View(timeout=60.0)
        
        async def hit_callback(interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                
            # Draw new card
            player_hand.append(self._draw_card())
            
            # Check for bust
            player_total = self._hand_value(player_hand)
            if player_total > 21:
                await db.update_wallet(user_id, -bet * (split_count + 1), interaction.guild.id)
                embed = self._blackjack_embed(
                    f"Bust! You lose {bet * (split_count + 1):,} {self.currency}",
                    player_hand,
                    dealer_hand,
                    bet,
                    -bet * (split_count + 1),
                    wallet - bet * (split_count + 1),
                    split_count
                )
                self.active_games.remove(user_id)
                return await interaction.response.edit_message(embed=embed, view=None)
                
            # Update message
            embed = self._blackjack_embed(
                "Your turn - Hit or Stand?",
                player_hand,
                [dealer_hand[0], "❓"],
                bet,
                0,
                wallet,
                split_count
            )
            await interaction.response.edit_message(embed=embed, view=view)
        
        async def stand_callback(interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                
            # Dealer draws until 17 or higher
            dealer_total = self._hand_value(dealer_hand)
            while dealer_total < 17:
                dealer_hand.append(self._draw_card())
                dealer_total = self._hand_value(dealer_hand)
                
            # Determine winner
            player_total = self._hand_value(player_hand)
            outcome = ""
            winnings = 0
            
            if dealer_total > 21:
                outcome = f"Dealer busts! You win {bet * (split_count + 1):,} {self.currency}"
                winnings = bet * (split_count + 1)
            elif player_total > dealer_total:
                outcome = f"You win {bet * (split_count + 1):,} {self.currency}!"
                winnings = bet * (split_count + 1)
            elif player_total < dealer_total:
                outcome = f"You lose {bet * (split_count + 1):,} {self.currency}!"
                winnings = -bet * (split_count + 1)
            else:
                outcome = "Push! Bet returned"
                winnings = 0
                
            # Update balance
            await db.update_wallet(user_id, winnings, interaction.guild.id)
            
            # Send final result
            embed = self._blackjack_embed(
                outcome,
                player_hand,
                dealer_hand,
                bet,
                winnings,
                wallet + winnings,
                split_count
            )
            self.active_games.remove(user_id)
            await interaction.response.edit_message(embed=embed, view=None)
        
        async def double_callback(interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                
            # Check if player can afford to double
            if wallet < bet * (split_count + 2):  # Original bet + new bet for each split
                return await interaction.response.send_message(
                    "❌ You don't have enough to double!", ephemeral=True)
                    
            # Double the bet and draw one card
            new_bet = bet * 2
            player_hand.append(self._draw_card())
            
            # Check for bust
            player_total = self._hand_value(player_hand)
            if player_total > 21:
                await db.update_wallet(user_id, -new_bet * (split_count + 1), interaction.guild.id)
                embed = self._blackjack_embed(
                    f"Bust! You lose {new_bet * (split_count + 1):,} {self.currency}",
                    player_hand,
                    dealer_hand,
                    new_bet,
                    -new_bet * (split_count + 1),
                    wallet - new_bet * (split_count + 1),
                    split_count
                )
                self.active_games.remove(user_id)
                return await interaction.response.edit_message(embed=embed, view=None)
                
            # Dealer draws until 17 or higher
            dealer_total = self._hand_value(dealer_hand)
            while dealer_total < 17:
                dealer_hand.append(self._draw_card())
                dealer_total = self._hand_value(dealer_hand)
                
            # Determine winner
            outcome = ""
            winnings = 0
            
            if dealer_total > 21:
                outcome = f"Dealer busts! You win {new_bet * (split_count + 1):,} {self.currency}"
                winnings = new_bet * (split_count + 1)
            elif player_total > dealer_total:
                outcome = f"You win {new_bet * (split_count + 1):,} {self.currency}!"
                winnings = new_bet * (split_count + 1)
            elif player_total < dealer_total:
                outcome = f"You lose {new_bet * (split_count + 1):,} {self.currency}!"
                winnings = -new_bet * (split_count + 1)
            else:
                outcome = "Push! Bet returned"
                winnings = 0
                
            # Update balance
            await db.update_wallet(user_id, winnings, interaction.guild.id)
            
            # Send final result
            embed = self._blackjack_embed(
                outcome,
                player_hand,
                dealer_hand,
                new_bet,
                winnings,
                wallet + winnings,
                split_count
            )
            self.active_games.remove(user_id)
            await interaction.response.edit_message(embed=embed, view=None)
        
        async def split_callback(interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                
            # Check if player can afford another split (max 4 hands)
            if split_count >= 3:  # Already split 3 times (total 4 hands)
                return await interaction.response.send_message(
                    "❌ You can't split more than 4 hands!", ephemeral=True)
                    
            if wallet < bet * (split_count + 2):  # Original bet + new bet for each split
                return await interaction.response.send_message(
                    "❌ You don't have enough to split again!", ephemeral=True)
                    
            # Split the hand into two hands
            hand1 = [player_hand[0], self._draw_card()]
            hand2 = [player_hand[1], self._draw_card()]
            
            # Create split queue
            split_queue = []
            if split_count > 0:
                # If we're already in a split, add to existing queue
                split_queue.extend(view.split_queue)
            split_queue.extend([hand1, hand2])
            
            # Create split game view
            view = self._blackjack_split_view(
                user_id,
                bet,
                split_queue,
                dealer_hand,
                wallet - bet,  # Original bet already deducted
                split_count + 1
            )
            
            embed = self._blackjack_split_embed(
                f"Split {1}/{len(split_queue)} - Hit or Stand?",
                split_queue[0],
                split_queue[1:] if len(split_queue) > 1 else None,
                [dealer_hand[0], "❓"],
                bet,
                0,
                wallet - bet,
                split_count + 1
            )
            
            await interaction.response.edit_message(embed=embed, view=view)
        
        hit_button = discord.ui.Button(label="Hit", style=discord.ButtonStyle.green)
        hit_button.callback = hit_callback
        view.add_item(hit_button)
        
        stand_button = discord.ui.Button(label="Stand", style=discord.ButtonStyle.red)
        stand_button.callback = stand_callback
        view.add_item(stand_button)
        
        # Only allow double on first move (2 cards)
        if len(player_hand) == 2:
            double_button = discord.ui.Button(label="Double", style=discord.ButtonStyle.blurple)
            double_button.callback = double_callback
            view.add_item(double_button)
            
            # Only allow split if cards have same value and we have < 4 hands
            if True: #self._can_split(player_hand) and split_count < 3
                split_button = discord.ui.Button(label="Split", style=discord.ButtonStyle.grey)
                split_button.callback = split_callback
                view.add_item(split_button)
                
        return view

    def _blackjack_split_view(self, user_id: int, bet: int, split_queue: list, dealer_hand: list, wallet: int, split_count: int):
        """Create a view for split hands with queue"""
        view = discord.ui.View(timeout=60.0)
        view.current_hand_index = 0
        view.split_queue = split_queue
        view.hands_completed = 0
        view.split_count = split_count
        
        async def hit_callback(interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                
            # Add card to current hand
            view.split_queue[view.current_hand_index].append(self._draw_card())
            current_hand = view.split_queue[view.current_hand_index]
            
            # Check for bust
            hand_value = self._hand_value(current_hand)
            if hand_value > 21:
                # Mark hand as done
                view.hands_completed += 1
                
                # Check if all hands are done
                if view.hands_completed == len(view.split_queue):
                    total_loss = bet * len(view.split_queue)
                    await db.update_wallet(user_id, -total_loss, interaction.guild.id)
                    embed = self._blackjack_split_embed(
                        f"All hands bust! You lose {total_loss:,} {self.currency}",
                        view.split_queue[0],
                        view.split_queue[1:],
                        dealer_hand,
                        bet,
                        -total_loss,
                        wallet - total_loss + bet,  # Original bet was already deducted
                        view.split_count
                    )
                    self.active_games.remove(user_id)
                    return await interaction.response.edit_message(embed=embed, view=None)
                else:
                    # Move to next hand
                    view.current_hand_index += 1
                    embed = self._blackjack_split_embed(
                        f"Split {view.current_hand_index + 1}/{len(view.split_queue)} - Hit or Stand?",
                        view.split_queue[view.current_hand_index],
                        [h for i, h in enumerate(view.split_queue) if i != view.current_hand_index],
                        [dealer_hand[0], "❓"],
                        bet,
                        0,
                        wallet,
                        view.split_count
                    )
                    return await interaction.response.edit_message(embed=embed, view=view)
                    
            # Update message
            embed = self._blackjack_split_embed(
                f"Split {view.current_hand_index + 1}/{len(view.split_queue)} - Hit or Stand?",
                view.split_queue[view.current_hand_index],
                [h for i, h in enumerate(view.split_queue) if i != view.current_hand_index],
                [dealer_hand[0], "❓"],
                bet,
                0,
                wallet,
                view.split_count
            )
            await interaction.response.edit_message(embed=embed, view=view)
        
        async def stand_callback(interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                
            # Mark current hand as done
            view.hands_completed += 1
            
            # Check if all hands are done
            if view.hands_completed == len(view.split_queue):
                # Dealer draws until 17 or higher
                dealer_total = self._hand_value(dealer_hand)
                while dealer_total < 17:
                    dealer_hand.append(self._draw_card())
                    dealer_total = self._hand_value(dealer_hand)
                    
                # Evaluate all hands
                results = []
                total_winnings = 0
                
                for hand in view.split_queue:
                    hand_value = self._hand_value(hand)
                    
                    if hand_value > 21:
                        results.append("Bust")
                        total_winnings -= bet
                    elif dealer_total > 21:
                        results.append("Win (Dealer bust)")
                        total_winnings += bet
                    elif hand_value > dealer_total:
                        results.append("Win")
                        total_winnings += bet
                    elif hand_value < dealer_total:
                        results.append("Lose")
                        total_winnings -= bet
                    else:
                        results.append("Push")
                        
                # Update balance
                await db.update_wallet(user_id, total_winnings, interaction.guild.id)
                
                # Create result message
                outcome = "\n".join(
                    f"Hand {i+1}: {result}" 
                    for i, result in enumerate(results)
                )
                outcome += f"\n\n**Net {'win' if total_winnings > 0 else 'loss'}: {abs(total_winnings):,} {self.currency}**"
                    
                embed = self._blackjack_split_embed(
                    outcome,
                    view.split_queue[0],
                    view.split_queue[1:],
                    dealer_hand,
                    bet,
                    total_winnings,
                    wallet + total_winnings + bet,  # Original bet was already deducted
                    view.split_count
                )
                self.active_games.remove(user_id)
                return await interaction.response.edit_message(embed=embed, view=None)
            else:
                # Move to next hand
                view.current_hand_index += 1
                embed = self._blackjack_split_embed(
                    f"Split {view.current_hand_index + 1}/{len(view.split_queue)} - Hit or Stand?",
                    view.split_queue[view.current_hand_index],
                    [h for i, h in enumerate(view.split_queue) if i != view.current_hand_index],
                    [dealer_hand[0], "❓"],
                    bet,
                    0,
                    wallet,
                    view.split_count
                )
                return await interaction.response.edit_message(embed=embed, view=view)
        
        hit_button = discord.ui.Button(label="Hit", style=discord.ButtonStyle.green)
        hit_button.callback = hit_callback
        view.add_item(hit_button)
        
        stand_button = discord.ui.Button(label="Stand", style=discord.ButtonStyle.red)
        stand_button.callback = stand_callback
        view.add_item(stand_button)
        
        return view

    def _blackjack_split_embed(self, title: str, current_hand: list, other_hands: list, dealer_hand: list, bet: int, winnings: int, new_balance: int, split_count: int):
        """Create a blackjack split game embed"""
        embed = discord.Embed(
            title=f"♠️♥️ Blackjack Game (Split {split_count}/{len(other_hands) + 1}) ♦️♣️ - {title}", 
            color=0x2b2d31
        )
        
        # Format hands
        current_hand_cards = " ".join([f"`{card}`" for card in current_hand])
        dealer_cards = " ".join([f"`{card}`" for card in dealer_hand])
        
        # Calculate totals
        current_hand_total = self._hand_value(current_hand)
        dealer_total = self._hand_value(dealer_hand) if "❓" not in dealer_hand else "?"
        
        embed.add_field(
            name=f"Current Hand ({current_hand_total})",
            value=current_hand_cards,
            inline=False
        )
        
        # Show other hands if they exist
        if other_hands and len(other_hands) > 0:
            other_hands_text = []
            for i, hand in enumerate(other_hands, 1):
                hand_cards = " ".join([f"`{card}`" for card in hand])
                hand_total = self._hand_value(hand)
                other_hands_text.append(f"**Hand {i} ({hand_total})**: {hand_cards}")
            
            embed.add_field(
                name="Other Hands",
                value="\n".join(other_hands_text),
                inline=False
            )
        
        embed.add_field(
            name=f"Dealer's Hand ({dealer_total})",
            value=dealer_cards,
            inline=False
        )
        
        # Add bet info
        embed.add_field(
            name="Bet per Hand",
            value=f"**{bet:,}** {self.currency}",
            inline=True
        )
        
        # Add winnings if game is over
        if winnings != 0:
            embed.add_field(
                name="Net Result",
                value=f"**{winnings:,}** {self.currency}",
                inline=True
            )
        
        embed.add_field(
            name="New Balance",
            value=f"**{new_balance:,}** {self.currency}",
            inline=True
        )
        
        return embed

    # Update the regular blackjack embed to include split count
    def _blackjack_embed(self, title: str, player_hand: list, dealer_hand: list, bet: int, winnings: int, new_balance: int, split_count: int = 0):
        """Create a blackjack game embed"""
        embed_title = f"♠️♥️ Blackjack Game"
        if split_count > 0:
            embed_title += f" (Split {split_count}/4)"
        embed_title += f" ♦️♣️ - {title}"
        
        embed = discord.Embed(title=embed_title, color=0x2b2d31)
        
        # Format hands
        player_cards = " ".join([f"`{card}`" for card in player_hand])
        dealer_cards = " ".join([f"`{card}`" for card in dealer_hand])
        
        # Calculate totals if not hidden
        player_total = self._hand_value(player_hand)
        dealer_total = self._hand_value(dealer_hand) if "❓" not in dealer_hand else "?"
        
        embed.add_field(
            name=f"Your Hand ({player_total})",
            value=player_cards,
            inline=False
        )
        embed.add_field(
            name=f"Dealer's Hand ({dealer_total})",
            value=dealer_cards,
            inline=False
        )
        
        # Add bet info
        bet_amount = bet * (split_count + 1) if split_count > 0 else bet
        embed.add_field(
            name="Bet",
            value=f"**{bet_amount:,}** {self.currency}",
            inline=True
        )
        
        # Add winnings if game is over
        if winnings != 0:
            embed.add_field(
                name="Result",
                value=f"**{winnings:,}** {self.currency}",
                inline=True
            )
        
        embed.add_field(
            name="New Balance",
            value=f"**{new_balance:,}** {self.currency}",
            inline=True
        )
        
        return embed

    def _draw_card(self) -> str:
        """Draw a random card"""
        value = random.choice(self.values)
        suit = random.choice(self.suits)
        return f"{value}{suit}"

    def _hand_value(self, hand: list) -> int:
        """Calculate the value of a hand"""
        value = 0
        aces = 0
        
        for card in hand:
            if isinstance(card, str) and card != "❓":
                card_value = card[:-1]  # Remove suit
                if card_value in ["J", "Q", "K"]:
                    value += 10
                elif card_value == "A":
                    value += 11
                    aces += 1
                else:
                    value += int(card_value)
        
        # Adjust for aces if over 21
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
            
        return value

    def _check_blackjack(self, hand: list) -> bool:
        """Check if hand is a blackjack (21 with 2 cards)"""
        return len(hand) == 2 and self._hand_value(hand) == 21

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crash(self, ctx, bet: str, auto_cashout: MultiplierConverter = None):
        """Bet on a multiplier that can crash at any moment
        `.crash all 1.2x` <- put it all on crash, and auto cashout when it hits 1.2x (Wont work because it must be at least 1.35x!)
        `.crash 500 1.5` <- bet 500 with auto cashout at 1.5x
        """
        if ctx.author.id in self.active_games:
            return await ctx.reply("❌ You already have an active game!")

        elif auto_cashout: 
            if auto_cashout > 0 and auto_cashout < 1.35 or auto_cashout < 0:
                return await ctx.reply("❌ Autocashout must be greater than 1.35!")
        self.active_games.add(ctx.author.id)
        
        try:
            # Parse bet amount
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            parsed_bet = await self._parse_bet(bet, wallet)
            
            if not parsed_bet:
                self.active_games.remove(ctx.author.id)
                return await ctx.reply("❌ Invalid bet amount!")

            if parsed_bet <= 0:
                return await ctx.reply("❌ Bet amount must be greater than 0!")

            if parsed_bet > wallet:
                self.active_games.remove(ctx.author.id)
                return await ctx.reply("❌ You don't have enough money for that bet!")
                
            # Deduct bet immediately
            await db.update_wallet(ctx.author.id, -parsed_bet, ctx.guild.id)
            self.stats_logger.log_command_usage("crash")  # Log command usage
            
            # Create crash game
            view = self._crash_view(ctx.author.id, parsed_bet, wallet - parsed_bet)
            embed = self._crash_embed(ctx.author.name, 1.0, parsed_bet, wallet - parsed_bet, False)
            
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
            # Start crash sequence
            await self._run_crash_game(ctx, view, parsed_bet, wallet - parsed_bet, auto_cashout)
            
        except Exception as e:
            self.logger.error(f"Crash error: {e}")
            if ctx.author.id in self.active_games:
                self.active_games.remove(ctx.author.id)
            await ctx.send("❌ An error occurred while starting the game.")

    async def _run_crash_game(self, ctx, view, bet: int, current_balance: int, auto_cashout: float = None):
        """Run the crash game sequence with exact crash points"""
        multiplier = 1.0
        increment = 0.1
        crash_point = random.uniform(1.1, 2.0)  # Determine crash point first

        # 1 in 1000 chance for a big multiplier
        if random.random() < 0.001:
            crash_point = random.uniform(10.0, 1000000.0)
        
        while True:
            # First check if we've reached crash point
            if multiplier >= crash_point:
                # Crashed exactly at crash_point
                embed = self._crash_embed(
                    ctx.author.name,
                    crash_point,
                    bet,
                    current_balance,
                    True,
                    f"💥 Crashed at {crash_point:.2f}x!"
                )
                self.active_games.remove(ctx.author.id)
                return await view.message.edit(embed=embed, view=None)
                
            # Then check for cashout (only possible if we haven't crashed yet)
            if view.cashed_out or (auto_cashout and multiplier >= auto_cashout):
                cashout_value = view.current_multiplier if view.cashed_out else auto_cashout
                winnings = int(bet * cashout_value)
                await db.update_wallet(ctx.author.id, winnings, ctx.guild.id)
                
                # Calculate how close they were to crashing
                percent_to_crash = (cashout_value / crash_point) * 100
                closeness = f"{percent_to_crash:.0f}% to crash point"
                
                status_msg = (f"💰 Cashed out at {cashout_value:.2f}x!" if view.cashed_out 
                            else f"🔄 Auto-cashed out at {auto_cashout:.2f}x!")
                
                embed = self._crash_embed(
                    ctx.author.name,
                    cashout_value,
                    bet,
                    current_balance + winnings,
                    True,
                    f"{status_msg}\n\n"
                    f"💡 Game would have crashed at {crash_point:.2f}x ({closeness})"
                )
                self.active_games.remove(ctx.author.id)
                return await view.message.edit(embed=embed, view=None)
                
            # Update multiplier (but never beyond crash_point)
            multiplier = min(multiplier + increment, crash_point)
            increment = max(0.01, increment * 0.99)
            view.current_multiplier = multiplier
            
            # Update display
            embed = self._crash_embed(ctx.author.name, multiplier, bet, current_balance, False)
            try:
                await view.message.edit(embed=embed)
            except discord.NotFound:
                self.active_games.remove(ctx.author.id)
                return
                
            await asyncio.sleep(0.75)
    def _crash_view(self, user_id: int, bet: int, current_balance: int):
        """Create the crash game view with cashout button"""
        view = discord.ui.View(timeout=30.0)
        view.cashed_out = False
        view.cashout_multiplier = 1.0
        view.current_multiplier = 1.0  # Track current multiplier
        
        async def cashout_callback(interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                
            view.cashed_out = True
            view.cashout_multiplier = view.current_multiplier  # Use the tracked multiplier
            await interaction.response.defer()
        
        cashout_button = discord.ui.Button(label="Cash Out", style=discord.ButtonStyle.green)
        cashout_button.callback = cashout_callback
        view.add_item(cashout_button)
        
        return view

    def _crash_embed(self, author:str, multiplier: float, bet: int, balance: int, game_over: bool, status: str = None):
        """Create a crash game embed"""
        color = 0x2ecc71 if not game_over else 0xe74c3c
        title = f"{author.capitalize()}'s 🚀 Crash Game" if not game_over else "💥 Game Over"
        
        embed = discord.Embed(title=title, color=color)
        
        if status:
            embed.description = f"**{status}**"
        
        embed.add_field(
            name="Current Multiplier",
            value=f"**{multiplier:.2f}x**",
            inline=True
        )
        
        embed.add_field(
            name="Potential Win",
            value=f"**{int(bet * multiplier):,}** {self.currency}",
            inline=True
        )
        
        embed.add_field(
            name="Your Balance",
            value=f"**{balance:,}** {self.currency}",
            inline=True
        )
        
        if not game_over:
            embed.set_footer(text="Cash out before the game crashes!")
        
        return embed

    @commands.command(aliases=['cf', 'flip'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coinflip(self, ctx, bet: str, choice: str = None):
        """Flip a coin - heads or tails"""
        try:
            # Parse bet amount
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            parsed_bet = await self._parse_bet(bet, wallet)
            
            if not parsed_bet:
                return await ctx.reply("❌ Invalid bet amount!")
                
            if parsed_bet <= 0:
                return await ctx.reply("❌ Bet amount must be greater than 0!")

            if parsed_bet > wallet:
                return await ctx.reply("❌ You don't have enough money for that bet!")
                
            # Validate choice
            if not choice:
                embed = discord.Embed(
                    title="🪙 Coin Flip",
                    description=f"Bet: **{parsed_bet:,}** {self.currency}\n\n"
                               f"Choose heads or tails:\n"
                               f"`{ctx.prefix}coinflip {bet} heads`\n"
                               f"`{ctx.prefix}coinflip {bet} tails`",
                    color=0xf1c40f
                )
                return await ctx.reply(embed=embed)
                
            choice = choice.lower()
            if choice not in ["heads", "tails", "h", "t"]:
                return await ctx.reply("❌ Invalid choice! Must be 'heads' or 'tails'")
                
            # Convert shorthand
            if choice == "h":
                choice = "heads"
            elif choice == "t":
                choice = "tails"
                
            # Flip coin
            result = random.choice(["heads", "tails"])
            win = choice == result
            
            # Calculate winnings
            if win:
                winnings = parsed_bet
                outcome = f"**You won {parsed_bet:,}** {self.currency}!"
                self.stats_logger.log_economy_transaction(ctx.author.id, "coinflip", winnings, True)  # Log win
            else:
                winnings = -parsed_bet
                outcome = f"**You lost {parsed_bet:,}** {self.currency}!"
                self.stats_logger.log_economy_transaction(ctx.author.id, "coinflip", parsed_bet, False)  # Log loss
                
            # Update balance
            await db.update_wallet(ctx.author.id, winnings, ctx.guild.id)
            self.stats_logger.log_command_usage("coinflip")  # Log command usage
            
            # Send result
            embed = discord.Embed(
                title=f"🪙 {'You win!' if win else 'You lose!'}",
                description=f"Your choice: **{choice.title()}**\n"
                          f"Result: **{result.title()}**\n\n"
                          f"{outcome}",
                color=0x2ecc71 if win else 0xe74c3c
            )
            
            embed.add_field(
                name="New Balance",
                value=f"**{wallet + winnings:,}** {self.currency}",
                inline=True
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Coinflip error: {e}")
            await ctx.reply("❌ An error occurred while processing your bet.")

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def slots(self, ctx, bet: str):
        """Play the slot machine"""
        try:
            # Parse bet amount
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            parsed_bet = await self._parse_bet(bet, wallet)
            
            if not parsed_bet:
                return await ctx.reply("❌ Invalid bet amount!")
            
            if parsed_bet <= 0:
                return await ctx.reply("❌ Bet amount must be greater than 0!")
        
            if parsed_bet > wallet:
                return await ctx.reply("❌ You don't have enough money for that bet!")
                
            # Deduct bet
            await db.update_wallet(ctx.author.id, -parsed_bet, ctx.guild.id)
            self.stats_logger.log_command_usage("slots")  # Log command usage
            
            # Spin the slots
            reels = []
            total_weight = sum(weight for _, weight in self.slot_symbols)
            
            for _ in range(3):
                rand = random.uniform(0, total_weight)
                current = 0
                for symbol, weight in self.slot_symbols:
                    current += weight
                    if rand <= current:
                        reels.append(symbol)
                        break
            
            # Calculate winnings
            winnings = 0
            outcome = "You lost!"
            
            # Check for wins
            if reels[0] == reels[1] == reels[2]:
                if reels[0] == "💎":
                    multiplier = 100
                    outcome = "JACKPOT! 💎💎💎"
                elif reels[0] == "7️⃣":
                    multiplier = 20
                    outcome = "TRIPLE 7s! 🎰"
                elif reels[0] == "🔔":
                    multiplier = 10
                    outcome = "TRIPLE BELLS! 🔔"
                else:
                    multiplier = 5
                    outcome = "TRIPLE MATCH!"
                    
                winnings = parsed_bet * multiplier
            elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
                multiplier = 2
                winnings = parsed_bet * multiplier
                outcome = "DOUBLE MATCH!"
                
            # Update balance if won
            if winnings > 0:
                await db.update_wallet(ctx.author.id, winnings, ctx.guild.id)
                self.stats_logger.log_economy_transaction(ctx.author.id, "slots", winnings, True)  # Log win
            else:
                self.stats_logger.log_economy_transaction(ctx.author.id, "slots", parsed_bet, False)  # Log loss
                
            # Create slot display
            slot_display = " | ".join(reels)
            
            embed = discord.Embed(
                title="🎰 Slot Machine",
                description=f"**{slot_display}**\n\n"
                          f"**{outcome}**\n"
                          f"Bet: **{parsed_bet:,}** {self.currency}\n"
                          f"Won: **{winnings:,}** {self.currency}",
                color=0x9b59b6
            )
            
            embed.add_field(
                name="New Balance",
                value=f"**{wallet - parsed_bet + winnings:,}** {self.currency}",
                inline=True
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Slots error: {e}")
            await ctx.reply("❌ An error occurred while spinning the slots.")

    @commands.command(aliases=['double', 'don', 'dbl'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def doubleornothing(self, ctx, *, items: str = None):
        """Double your items or lose them"""
        if ctx.author.id in self.active_games:
            return await ctx.reply("❌ You already have an active game!")
            
        if not items:
            return await ctx.reply(f"Usage: `{ctx.prefix}doubleornothing <item1> [item2] ... [item20]`")
            
        try:
            # Get user inventory
            inventory = await db.get_inventory(ctx.author.id, ctx.guild.id)
            if not inventory:
                return await ctx.reply("❌ Your inventory is empty!")
                
            # Parse requested items
            requested_items = items.split()
            if len(requested_items) > 20:
                return await ctx.reply("❌ You can only bet up to 20 items at a time!")
                
            # Find matching items in inventory
            items_to_bet = []
            for item_name in requested_items:
                found = False
                for item in inventory:
                    if not isinstance(item, dict):
                        continue
                    if (item.get("id", "").lower() == item_name.lower() or 
                        item.get("name", "").lower() == item_name.lower()):
                        items_to_bet.append(item)
                        found = True
                        break
                        
                if not found:
                    return await ctx.reply(f"❌ You don't have '{item_name}' in your inventory!")
                    
            # Create confirmation view
            view = discord.ui.View(timeout=30.0)
            
            async def confirm_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                    
                # Flip coin (50% chance)
                win = random.choice([True, False])
                
                if win:
                    # Double the items
                    for item in items_to_bet:
                        await db.add_to_inventory(
                            ctx.author.id, 
                            ctx.guild.id, 
                            item, 
                            item.get("quantity", 1)
                        )
                        
                    outcome = f"**You won!** All items doubled!"
                    self.stats_logger.log_economy_transaction(
                        ctx.author.id, 
                        "doubleornothing", 
                        sum(item.get("value", 0) for item in items_to_bet), 
                        True
                    )  # Log win (approximate value)
                else:
                    # Remove the items
                    for item in items_to_bet:
                        await db.remove_from_inventory(
                            ctx.author.id, 
                            ctx.guild.id, 
                            item.get("id", item.get("name")), 
                            item.get("quantity", 1)
                        )
                        
                    outcome = "**You lost!** All items are gone!"
                    self.stats_logger.log_economy_transaction(
                        ctx.author.id, 
                        "doubleornothing", 
                        sum(item.get("value", 0) for item in items_to_bet), 
                        False
                    )  # Log loss (approximate value)
                    
                # Log command usage
                self.stats_logger.log_command_usage("doubleornothing")
                
                # Create result embed
                item_names = ", ".join([item.get("name", "Unknown") for item in items_to_bet])
                
                embed = discord.Embed(
                    title="🎲 Double or Nothing",
                    description=f"You bet: **{item_names}**\n\n"
                            f"{outcome}",
                    color=0x2ecc71 if win else 0xe74c3c
                )
                
                await interaction.response.edit_message(embed=embed, view=None)
                self.active_games.remove(ctx.author.id)
                
            async def cancel_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                    
                await interaction.response.edit_message(content="❌ Game cancelled.", embed=None, view=None)
                self.active_games.remove(ctx.author.id)
                
            confirm_button = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.green)
            confirm_button.callback = confirm_callback
            view.add_item(confirm_button)
            
            cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red)
            cancel_button.callback = cancel_callback
            view.add_item(cancel_button)
            
            # Create confirmation message
            item_names = ", ".join([item.get("name", "Unknown") for item in items_to_bet])
            
            embed = discord.Embed(
                title="🎲 Double or Nothing",
                description=f"You're about to bet:\n**{item_names}**\n\n"
                        f"50% chance to double them, 50% chance to lose them all!",
                color=0xf39c12
            )
            
            self.active_games.add(ctx.author.id)
            await ctx.reply(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Double or nothing error: {e}")
            if ctx.author.id in self.active_games:
                self.active_games.remove(ctx.author.id)
            await ctx.reply("❌ An error occurred while setting up the game.")
            
    @commands.command(aliases=['rlt'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roulette(self, ctx, bet: str = None, choice: str = None):
        """Play roulette - bet on numbers, colors, or odd/even"""
        if bet is None or choice is None:
            # Show help menu if no args provided
            embed = discord.Embed(
                title="🎡 Roulette Help",
                description="Place bets on numbers, colors, or other options in roulette.",
                color=0x3498db
            )
            
            embed.add_field(
                name="💰 Bet Types & Payouts",
                value=(
                    "`number (0-36)` - 35:1 payout\n"
                    "`red`/`black` - 1:1 payout\n"
                    "`green` (0) - 35:1 payout\n"
                    "`even`/`odd` - 1:1 payout\n"
                    "`1st12`/`2nd12`/`3rd12` - 2:1 payout\n"
                    "`1-18`/`19-36` - 1:1 payout"
                ),
                inline=False
            )
            
            embed.add_field(
                name="📝 Usage Examples",
                value=(
                    "`.rlt 500 red` - Bet 500 on red\n"
                    "`.rlt all 7` - Bet everything on number 7\n"
                    "`.rlt half odd` - Bet half your balance on odd\n"
                    "`.rlt 1k 1st12` - Bet 1,000 on first dozen (1-12)"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💡 Bet Amount Options",
                value=(
                    "You can bet using:\n"
                    "- Exact amounts (`500`)\n"
                    "- `all` or `max` (your entire balance)\n"
                    "- `half` (half your balance)\n"
                    "- Percentages (`50%`)\n"
                    "- Suffixes (`1k` = 1,000, `1.5m` = 1,500,000)"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Current balance: {await db.get_wallet_balance(ctx.author.id, ctx.guild.id):,} {self.currency}")
            return await ctx.reply(embed=embed)
        
        try:
            # Parse bet amount
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            parsed_bet = await self._parse_bet(bet, wallet)
            
            if not parsed_bet:
                return await ctx.reply("❌ Invalid bet amount!")
            
            if parsed_bet <= 0:
                return await ctx.reply("❌ Bet amount must be greater than 0! \n-# *(Do you have $0 in your wallet?)*")
                
            if parsed_bet > wallet:
                return await ctx.reply("❌ You don't have enough money for that bet!")
                
            # Parse choice
            choice = choice.lower()
            # In the valid_choices dictionary, change the multipliers for red/black/even/odd from 1 to 2
            valid_choices = {
                "red": ("color", 2, "Red"),        # Changed from 1 to 2
                "black": ("color", 2, "Black"),    # Changed from 1 to 2
                "green": ("color", 35, "Green (0)"),
                "even": ("even", 2, "Even"),      # Changed from 1 to 2
                "odd": ("odd", 2, "Odd"),          # Changed from 1 to 2
                "1st12": ("dozen", 2, "1st 12"),
                "2nd12": ("dozen", 2, "2nd 12"),
                "3rd12": ("dozen", 2, "3rd 12"),
                "1-18": ("half", 2, "1-18"),       # Changed from 1 to 2
                "19-36": ("half", 2, "19-36")      # Changed from 1 to 2
            }
            
            # Check for number bet
            number_bet = None
            try:
                number = int(choice)
                if 0 <= number <= 36:
                    number_bet = ("number", 35, f"Number {number}")
            except ValueError:
                pass
                
            if not number_bet and choice not in valid_choices:
                return await ctx.reply(
                    "❌ Invalid bet type!\n"
                    "Valid bets: `number (0-36)`, `red`, `black`, `green`, `even`, `odd`, "
                    "`1st12`, `2nd12`, `3rd12`, `1-18`, `19-36`"
                )
                
            bet_type, multiplier, bet_name = number_bet if number_bet else valid_choices[choice]
            
            # Deduct bet
            await db.update_wallet(ctx.author.id, -parsed_bet, ctx.guild.id)
            
            # Create initial embed
            embed = discord.Embed(
                title="🎡 Roulette - Spinning...",
                description=f"**Your bet:** {bet_name}\n"
                        f"**Bet amount:** {parsed_bet:,} {self.currency}\n"
                        f"**Potential win:** {parsed_bet * multiplier:,} {self.currency}\n\n"
                        f"The wheel is spinning...",
                color=0xf39c12
            )
            message = await ctx.reply(embed=embed)
            
            # Animation sequence
            spin_duration = 5  # seconds
            spin_steps = 10
            delay = spin_duration / spin_steps
            
            # Generate the final result first
            winning_number, winning_color = random.choice(self.roulette_numbers)
            
            # Create animation steps
            for i in range(spin_steps):
                # Show random numbers during spin
                anim_number, anim_color = random.choice(self.roulette_numbers)
                
                # Gradually slow down the animation
                if i > spin_steps * 0.7:  # Last 30% of spins
                    # Start homing in on the actual result
                    if random.random() < 0.3 + (i/spin_steps):
                        anim_number, anim_color = winning_number, winning_color
                
                embed.description = (
                    f"**Your bet:** {bet_name}\n"
                    f"**Bet amount:** {parsed_bet:,} {self.currency}\n"
                    f"**Potential win:** {parsed_bet * multiplier:,} {self.currency}\n\n"
                    f"**The ball is rolling...**\n"
                    f"Current position: {anim_number} {anim_color.title()}"
                )
                
                # Make the wheel appear to slow down
                if i == spin_steps - 1:
                    embed.title = "🎡 Roulette - Almost there..."
                elif i > spin_steps * 0.8:
                    embed.title = "🎡 Roulette - Slowing down..."
                
                # Use rate-limited editing instead of direct edit
                await self.queue_message_edit(message, embed)
                await asyncio.sleep(delay)
            
            # Determine if bet won
            win = False
            if bet_type == "number":
                win = winning_number == number
            elif bet_type == "color":
                win = winning_color == choice
            elif bet_type == "even":
                win = winning_number != 0 and winning_number % 2 == 0
            elif bet_type == "odd":
                win = winning_number % 2 == 1
            elif bet_type == "dozen":
                dozen = int(choice[:1])  # 1, 2, or 3
                win = (dozen - 1) * 12 < winning_number <= dozen * 12
            elif bet_type == "half":
                if choice == "1-18":
                    win = 1 <= winning_number <= 18
                else:
                    win = 19 <= winning_number <= 36
                    
            # Calculate winnings
            if win:
                winnings = parsed_bet * multiplier
                outcome = f"**You won {winnings:,}** {self.currency}!"
                self.stats_logger.log_economy_transaction(ctx.author.id, "roulette", winnings, True)  # Log win
            else:
                winnings = -parsed_bet
                outcome = f"**You lost {parsed_bet:,}** {self.currency}!"
                self.stats_logger.log_economy_transaction(ctx.author.id, "roulette", parsed_bet, False)  # Log loss
                
            # Update balance
            if winnings > 0:
                await db.update_wallet(ctx.author.id, winnings, ctx.guild.id)
                
            # Create final result embed
            result_color = 0xe74c3c if winning_color == "red" else 0x2c3e50 if winning_color == "black" else 0x2ecc71
            
            embed = discord.Embed(
                title=f"🎡 Roulette - {'Winner!' if win else 'Better luck next time!'}",
                description=f"**The ball landed on:**\n"
                        f"**{winning_number} {winning_color.title()}**\n\n"
                        f"**Your bet:** {bet_name}\n"
                        f"**Bet amount:** {parsed_bet:,} {self.currency}\n"
                        f"**Multiplier:** {multiplier}x\n\n"
                        f"{outcome}",
                color=result_color
            )
            
            embed.add_field(
                name="New Balance",
                value=f"**{wallet - parsed_bet + (winnings if win else 0):,}** {self.currency}",
                inline=True
            )
            
            # Add different emojis based on result
            if win:
                embed.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/160/twitter/259/party-popper_1f389.png")
            else:
                embed.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/160/twitter/259/pensive-face_1f614.png")
            
            await message.edit(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Roulette error: {e}")
            await ctx.reply("❌ An error occurred while processing your bet.")

    @commands.command(aliases=['bomb_activate'])
    @commands.cooldown(1, 300, commands.BucketType.guild)
    async def bomb(self, ctx, channel: discord.TextChannel = None, amount: int = 1000):
        """💣 Start a money bomb (Duration scales with investment)
        
        Parameters:
        channel: Target channel (#mention)
        amount: Investment (1000-1M coins, default: 1000)
        """
        # Validation checks
        if channel is None:
            embed = discord.Embed(
                color=0xFF0000,
                description=f"{ctx.author.mention}, please specify a channel: `!bomb #channel [amount]`"
            )
            return await ctx.send(embed=embed)
        
        if not isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                color=0xFF0000,
                description=f"{ctx.author.mention}, you must specify a valid text channel!"
            )
            return await ctx.send(embed=embed)
        
        if not channel.permissions_for(ctx.guild.me).send_messages:
            embed = discord.Embed(
                color=0xFF0000,
                description=f"{ctx.author.mention}, I don't have permission to send messages in {channel.mention}!"
            )
            return await ctx.send(embed=embed)
        
        # Amount validation
        amount = max(1000, min(1000000, amount))  # Clamp between 1k-1M
        wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        
        if wallet < amount:
            embed = discord.Embed(
                color=0xFF0000,
                description=f"💸 {ctx.author.mention} You need **{amount:,}** {self.currency} (You have: {wallet:,})"
            )
            return await ctx.send(embed=embed)
        
        # Calculate duration (linear scaling, max 10min at 1M)
        base_duration = 60  # 1 minute at 1k coins
        max_duration = 600  # 10 minutes at 1M coins
        duration = min(max_duration, base_duration * (amount / 1000))
        
        # Deduct bomb cost
        await db.update_wallet(ctx.author.id, -amount, ctx.guild.id)
        
        # Bomb activation embed
        bomb_embed = discord.Embed(
            title="💣 **DYNAMIC MONEY BOMB** 💣",
            color=0xFF5733,
            description=(
                f"**Investor:** {ctx.author.mention}\n"
                f"**Investment:** {amount:,} {self.currency}\n"
                f"**Duration:** {int(duration)} seconds\n\n"
                "🚨 **ANY MESSAGE HAS 50% CHANCE TO EXPLODE** 💥\n"
                f"💰 **Potential Payout:** Up to {amount*2:,} {self.currency}"
            )
        )
        bomb_msg = await channel.send(embed=bomb_embed)
        
        # Game tracking
        victims = {}
        first_time_victims = set()
        bomber_bank = 0
        end_time = datetime.now() + timedelta(seconds=duration)
        
        def is_bomb_active():
            return datetime.now() < end_time
        
        # Real-time duration updater
        async def update_timer():
            while is_bomb_active():
                time_left = max(0, (end_time - datetime.now()).total_seconds())
                if time_left % 30 == 0 or time_left <= 10:  # Update every 30s or last 10s
                    await bomb_msg.edit(embed=bomb_embed.set_footer(
                        text=f"⏰ Time remaining: {int(time_left)} seconds | Current victims: {len(victims)}"
                    ))
                await asyncio.sleep(1)
        
        timer_task = self.bot.loop.create_task(update_timer())
        
        # Main game loop
        try:
            while is_bomb_active():
                try:
                    msg = await self.bot.wait_for(
                        'message',
                        check=lambda m: (
                            m.channel == channel and
                            not m.author.bot and
                            m.author != ctx.author and
                            is_bomb_active()
                        ),
                        timeout=0.5
                    )
                    
                    if random.random() < 0.5:
                        # Scale loss with investment (40-75 at 1k, up to 400-750 at 1M)
                        loss_multiplier = min(10, amount / 1000)
                        amount_lost = random.randint(
                            int(40 * loss_multiplier),
                            int(75 * loss_multiplier)
                        )
                        victims[msg.author.id] = victims.get(msg.author.id, 0) + amount_lost
                        bomber_bank += amount_lost
                        
                        if msg.author.id not in first_time_victims:
                            first_time_victims.add(msg.author.id)
                            await msg.add_reaction('💥')
                            await msg.add_reaction('💸')
                            
                except asyncio.TimeoutError:
                    continue
                    
        finally:
            timer_task.cancel()
        
        # Payout calculation (up to 2x investment)
        payout = min(amount*2, bomber_bank)
        await db.update_bank(ctx.author.id, payout, ctx.guild.id)
        
        # Results embed
        result_embed = discord.Embed(
            title=f"💥 **BOMB COMPLETED** 💥",
            color=0xFFA500,
            description=(
                f"**Investment:** {amount:,} {self.currency}\n"
                f"**Duration:** {int(duration)} seconds\n"
                f"**Total Payout:** {payout:,} {self.currency}\n"
                f"**ROI:** {((payout/amount)*100)-100:.1f}%\n\n"
                f"**Next Upgrade:** {int(amount*1.5):,} {self.currency} = {min(720, int(duration*1.5))} seconds"
            )
        )
        
        if victims:
            top_victims = sorted(victims.items(), key=lambda x: x[1], reverse=True)[:5]
            result_embed.add_field(
                name="🔥 Top Victims",
                value="\n".join(
                    f"{self.bot.get_user(vid).mention} ─ **{amt:,}** {self.currency}"
                    for vid, amt in top_victims
                ),
                inline=False
            )
        else:
            result_embed.add_field(
                name="Result",
                value="💨 No victims were caught!",
                inline=False
            )
        
        await channel.send(embed=result_embed)

    async def _parse_bet(self, bet_str: str, wallet: int) -> int:
        """Parse bet amount from string (supports all, half, %, k, m, b suffixes) with 250M cap"""
        try:
            bet_str = bet_str.lower().strip()
            MAX_BET = 250_000_000  # 250 million cap
            
            if bet_str in ['all', 'max']:
                # Cap 'all' bets at 250M if wallet is over 250M
                return min(wallet, MAX_BET)
            elif bet_str in ['half', '1/2']:
                # Half of wallet, but capped at 250M
                half_bet = wallet // 2
                return min(half_bet, MAX_BET)
            elif bet_str.endswith('%'):
                percent = float(bet_str[:-1])
                if percent <= 0 or percent > 100:
                    return None
                calculated_bet = int(wallet * (percent / 100))
                return min(calculated_bet, MAX_BET)
            elif bet_str.endswith('k'):
                calculated_bet = int(float(bet_str[:-1]) * 1000)
                return min(calculated_bet, MAX_BET)
            elif bet_str.endswith('m'):
                calculated_bet = int(float(bet_str[:-1]) * 1000000)
                return min(calculated_bet, MAX_BET)
            elif bet_str.endswith('b'):
                calculated_bet = int(float(bet_str[:-1]) * 1000000000)
                return min(calculated_bet, MAX_BET)
            else:
                calculated_bet = int(bet_str)
                return min(calculated_bet, MAX_BET)
        except (ValueError, AttributeError):
            return None

    async def process_message_edits(self):
        """Process message edits with rate limiting to prevent API overload"""
        while True:
            try:
                # Check if there are edits in queue
                if not self.message_edit_queue.empty():
                    # Get the next edit
                    edit_data = await self.message_edit_queue.get()
                    
                    # Check cooldown
                    message_id = edit_data.get('message_id')
                    current_time = time.time()
                    
                    if message_id in self.last_edit_time:
                        time_diff = current_time - self.last_edit_time[message_id]
                        if time_diff < self.edit_cooldown:
                            # Put it back in queue and wait
                            await asyncio.sleep(self.edit_cooldown - time_diff)
                    
                    # Perform the edit
                    try:
                        message = edit_data.get('message')
                        embed = edit_data.get('embed')
                        
                        if message and embed:
                            await message.edit(embed=embed)
                            self.last_edit_time[message_id] = current_time
                    
                    except discord.HTTPException as e:
                        if e.status == 429:  # Rate limited
                            # Put back in queue and increase cooldown
                            await self.message_edit_queue.put(edit_data)
                            self.edit_cooldown = min(self.edit_cooldown * 1.5, 30.0)
                            await asyncio.sleep(float(e.retry_after) if hasattr(e, 'retry_after') else 5)
                        else:
                            self.logger.error(f"Message edit error: {e}")
                    
                    # Mark task as done
                    self.message_edit_queue.task_done()
                
                await asyncio.sleep(0.5)  # Check queue every 500ms
                
            except Exception as e:
                self.logger.error(f"Error in message edit processor: {e}")
                await asyncio.sleep(1)

    async def queue_message_edit(self, message, embed):
        """Queue a message edit for rate-limited processing"""
        edit_data = {
            'message': message,
            'embed': embed,
            'message_id': message.id,
            'timestamp': time.time()
        }
        await self.message_edit_queue.put(edit_data)

    async def cleanup_active_games(self):
        """Clear active games queue every 15 minutes to prevent stuck games"""
        while True:
            try:
                await asyncio.sleep(900)  # 15 minutes = 900 seconds
                
                if self.active_games:
                    cleared_count = len(self.active_games)
                    self.active_games.clear()
                    self.logger.info(f"Cleared {cleared_count:,} stuck active games")
                    
            except Exception as e:
                self.logger.error(f"Error in active games cleanup: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

async def setup(bot):
    await bot.add_cog(Gambling(bot))
