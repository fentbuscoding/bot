#!/usr/bin/env python3
"""
Fishing Economy Simulation and Balance Analysis
Interactive testing suite for balancing fishing economy
"""

import sys
import os
import json
import random
import statistics
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add the bot directory to path so we can import the fishing modules
sys.path.insert(0, '/home/ks/Desktop/bot')

from cogs.economy.fishing.fishing_data import FishingData

@dataclass
class SimulationResult:
    """Results from a fishing simulation"""
    bait_name: str
    bait_id: str
    rod_name: str
    rod_id: str
    bait_cost: int
    cycles: int
    total_investment: int
    total_revenue: int
    net_profit: int
    roi_percentage: float
    avg_profit_per_cast: float
    fish_caught: int
    fish_escaped: int
    catch_rate: float
    rarity_breakdown: Dict[str, int]
    avg_fish_value: float
    recommendation: str
    timestamp: str = ""

@dataclass 
class CombinedData:
    """Combined data from multiple simulation runs"""
    total_runs: int
    total_cycles: int
    combined_results: List[SimulationResult]
    run_history: List[dict]
    created_at: str
    last_updated: str

class FishingSimulator:
    """Simulates fishing to analyze economy balance"""
    
    def __init__(self):
        self.data_manager = FishingData()
        self.rod_data = self.data_manager.get_rod_data()
        self.bait_data = self.data_manager.get_bait_data()
        self.fish_database = self.data_manager.get_fish_database()
        
        # Load bait costs from shop data
        self.bait_costs = self._load_bait_costs()
        
        # Data persistence
        self.data_file = Path('fishing_simulation_combined_data.json')
        self.combined_data = self._load_combined_data()
        
        print(f"Loaded {len(self.rod_data)} rods, {len(self.bait_data)} baits, {sum(len(fish_list) for fish_list in self.fish_database.values())} fish types")
        if self.combined_data.total_runs > 0:
            print(f"Previous data: {self.combined_data.total_runs} runs, {self.combined_data.total_cycles:,} total cycles")
    
    def _load_combined_data(self) -> CombinedData:
        """Load existing combined data or create new"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                # Convert to CombinedData object
                combined_results = []
                for result_data in data.get('combined_results', []):
                    result = SimulationResult(**result_data)
                    combined_results.append(result)
                
                return CombinedData(
                    total_runs=data.get('total_runs', 0),
                    total_cycles=data.get('total_cycles', 0),
                    combined_results=combined_results,
                    run_history=data.get('run_history', []),
                    created_at=data.get('created_at', datetime.now().isoformat()),
                    last_updated=data.get('last_updated', datetime.now().isoformat())
                )
            except Exception as e:
                print(f"Error loading combined data: {e}")
        
        # Create new combined data
        return CombinedData(
            total_runs=0,
            total_cycles=0,
            combined_results=[],
            run_history=[],
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
    
    def _save_combined_data(self):
        """Save combined data to file"""
        try:
            data = {
                'total_runs': self.combined_data.total_runs,
                'total_cycles': self.combined_data.total_cycles,
                'combined_results': [
                    {
                        'bait_name': r.bait_name,
                        'bait_id': r.bait_id,
                        'rod_name': r.rod_name,
                        'rod_id': r.rod_id,
                        'bait_cost': r.bait_cost,
                        'cycles': r.cycles,
                        'total_investment': r.total_investment,
                        'total_revenue': r.total_revenue,
                        'net_profit': r.net_profit,
                        'roi_percentage': r.roi_percentage,
                        'avg_profit_per_cast': r.avg_profit_per_cast,
                        'fish_caught': r.fish_caught,
                        'fish_escaped': r.fish_escaped,
                        'catch_rate': r.catch_rate,
                        'rarity_breakdown': r.rarity_breakdown,
                        'avg_fish_value': r.avg_fish_value,
                        'recommendation': r.recommendation,
                        'timestamp': r.timestamp
                    } for r in self.combined_data.combined_results
                ],
                'run_history': self.combined_data.run_history,
                'created_at': self.combined_data.created_at,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ Combined data saved to {self.data_file}")
            
        except Exception as e:
            print(f"❌ Error saving combined data: {e}")
    
    def _load_bait_costs(self) -> Dict[str, int]:
        """Load bait costs from shop data"""
        try:
            bait_costs = {}
            
            # Load from JSON shop data
            json_path = Path('data/shop/bait.json')
            if json_path.exists():
                with open(json_path, 'r') as f:
                    shop_data = json.load(f)
                
                for bait_id, bait_info in shop_data.items():
                    # Calculate cost per unit
                    total_cost = bait_info.get('price', 0)
                    amount = bait_info.get('amount', 1)
                    cost_per_unit = total_cost / amount if amount > 0 else total_cost
                    bait_costs[bait_id] = int(cost_per_unit)
            
            # Add fallback costs for any missing baits
            for bait_id in self.bait_data.keys():
                if bait_id not in bait_costs:
                    bait_costs[bait_id] = 50  # Default cost
            
            return bait_costs
        except Exception as e:
            print(f"Error loading bait costs: {e}")
            return {}
    
    def simulate_fishing_cycle(self, bait_id: str, rod_id: str) -> Tuple[Optional[dict], bool, str]:
        """
        Simulate a single fishing cycle
        Returns: (fish_caught, rod_broke, outcome_type)
        """
        rod = self.rod_data[rod_id]
        bait = self.bait_data[bait_id]
        
        # Check rod durability
        rod_durability = rod.get('durability', 0.95)
        if random.random() > rod_durability:
            return None, True, 'rod_broke'
        
        # Get catch rates and apply rod multiplier
        bait_rates = bait.get('catch_rates', {})
        rod_multiplier = rod.get('multiplier', 1.0)
        adjusted_rates = self.data_manager.apply_rod_multiplier(bait_rates, rod_multiplier)
        
        # Roll for fish rarity
        total_weight = sum(adjusted_rates.values())
        if total_weight == 0:
            return None, False, 'no_bite'
        
        roll = random.random() * total_weight
        cumulative = 0
        caught_rarity = "junk"
        
        for rarity, weight in adjusted_rates.items():
            cumulative += weight
            if roll <= cumulative:
                caught_rarity = rarity
                break
        
        # Select specific fish from rarity
        if caught_rarity not in self.fish_database or not self.fish_database[caught_rarity]:
            caught_rarity = "junk"
        
        fish_list = self.fish_database.get(caught_rarity, [])
        if not fish_list:
            return None, False, 'no_fish_available'
        
        fish_template = random.choice(fish_list)
        
        # Check if fish escapes
        rod_power = rod.get('power', 1)
        base_escape_chance = fish_template.get('escape_chance', 0.1)
        
        # Reduce escape chance based on rod power
        power_reduction = min(0.8, (rod_power - 1) * 0.15)
        final_escape_chance = max(0.01, base_escape_chance * (1 - power_reduction))
        
        if random.random() < final_escape_chance:
            return None, False, 'fish_escaped'
        
        # Fish caught successfully
        min_weight = fish_template.get('min_weight', 0.1)
        max_weight = fish_template.get('max_weight', 1.0)
        weight = random.uniform(min_weight, max_weight)
        
        base_value = fish_template.get('base_value', 100)
        final_value = random.randint(int(base_value * 0.8), int(base_value * 1.2))
        
        fish = {
            'name': fish_template['name'],
            'rarity': caught_rarity,
            'value': final_value,
            'weight': weight
        }
        
        return fish, False, 'fish_caught'
    
    def simulate_bait_rod_combination(self, bait_id: str, rod_id: str, cycles: int = 1000) -> SimulationResult:
        """Simulate fishing for a specific bait/rod combination"""
        bait = self.bait_data[bait_id]
        rod = self.rod_data[rod_id]
        bait_cost = self.bait_costs.get(bait_id, 50)
        
        # Simulation tracking
        total_investment = cycles * bait_cost
        total_revenue = 0
        fish_caught = 0
        fish_escaped = 0
        rods_broken = 0
        rarity_breakdown = {}
        fish_values = []
        
        # Run simulation
        for cycle in range(cycles):
            fish, rod_broke, outcome = self.simulate_fishing_cycle(bait_id, rod_id)
            
            if rod_broke:
                rods_broken += 1
                # In real game, rod cost would be added to investment
                # For simulation, we assume infinite rods for cleaner analysis
            
            if fish:
                fish_caught += 1
                total_revenue += fish['value']
                fish_values.append(fish['value'])
                
                rarity = fish['rarity']
                rarity_breakdown[rarity] = rarity_breakdown.get(rarity, 0) + 1
            elif outcome == 'fish_escaped':
                fish_escaped += 1
        
        # Calculate metrics
        net_profit = total_revenue - total_investment
        roi_percentage = (net_profit / total_investment * 100) if total_investment > 0 else 0
        avg_profit_per_cast = net_profit / cycles if cycles > 0 else 0
        catch_rate = fish_caught / cycles if cycles > 0 else 0
        avg_fish_value = statistics.mean(fish_values) if fish_values else 0
        
        # Generate recommendation
        recommendation = self._generate_recommendation(roi_percentage, avg_profit_per_cast, catch_rate, bait_cost)
        
        return SimulationResult(
            bait_name=bait.get('name', bait_id),
            bait_id=bait_id,
            rod_name=rod.get('name', rod_id),
            rod_id=rod_id,
            bait_cost=bait_cost,
            cycles=cycles,
            total_investment=total_investment,
            total_revenue=total_revenue,
            net_profit=net_profit,
            roi_percentage=roi_percentage,
            avg_profit_per_cast=avg_profit_per_cast,
            fish_caught=fish_caught,
            fish_escaped=fish_escaped,
            catch_rate=catch_rate,
            rarity_breakdown=rarity_breakdown,
            avg_fish_value=avg_fish_value,
            recommendation=recommendation,
            timestamp=datetime.now().isoformat()
        )
    
    def _generate_recommendation(self, roi: float, avg_profit: float, catch_rate: float, bait_cost: int) -> str:
        """Generate balancing recommendation based on simulation results"""
        if roi > 1000:  # 1000%+ ROI
            return f"SEVERELY OVERPOWERED - Nerf by 60-80%"
        elif roi > 500:  # 500%+ ROI
            return f"OVERPOWERED - Nerf by 40-60%"
        elif roi > 200:  # 200%+ ROI
            return f"Too Strong - Nerf by 20-40%"
        elif roi > 100:  # 100%+ ROI
            return f"Slightly OP - Nerf by 10-20%"
        elif roi > 50:   # 50%+ ROI
            return f"Balanced - Good profit potential"
        elif roi > 0:    # Positive ROI
            return f"Underpowered - Buff by 10-30%"
        elif roi > -25:  # Small loss
            return f"Weak - Buff by 30-50%"
        else:            # Big loss
            return f"SEVERELY UNDERPOWERED - Buff by 50-100%"
    
    def run_full_simulation(self, cycles_per_combo: int = 1000) -> List[SimulationResult]:
        """Run simulation for all bait/rod combinations"""
        results = []
        total_combinations = len(self.bait_data) * len(self.rod_data)
        current = 0
        
        print(f"\nRunning simulation for {total_combinations} combinations ({cycles_per_combo} cycles each)...")
        print("=" * 80)
        
        start_time = time.time()
        
        for bait_id in self.bait_data.keys():
            for rod_id in self.rod_data.keys():
                current += 1
                print(f"Progress: {current}/{total_combinations} - Testing {bait_id} + {rod_id}")
                
                result = self.simulate_bait_rod_combination(bait_id, rod_id, cycles_per_combo)
                results.append(result)
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ Simulation completed in {elapsed_time:.1f} seconds")
        print(f"Total cycles simulated: {total_combinations * cycles_per_combo:,}")
        
        return results
    
    def combine_with_existing_data(self, new_results: List[SimulationResult]) -> None:
        """Combine new simulation results with existing data"""
        print("\n🔄 Combining with existing data...")
        
        # Create lookup for existing results
        existing_lookup = {}
        for result in self.combined_data.combined_results:
            key = f"{result.bait_id}_{result.rod_id}"
            existing_lookup[key] = result
        
        # Combine or add new results
        combined_results = []
        
        for new_result in new_results:
            key = f"{new_result.bait_id}_{new_result.rod_id}"
            
            if key in existing_lookup:
                # Combine with existing result
                existing = existing_lookup[key]
                
                # Calculate weighted averages and totals
                total_cycles = existing.cycles + new_result.cycles
                total_investment = existing.total_investment + new_result.total_investment
                total_revenue = existing.total_revenue + new_result.total_revenue
                total_fish_caught = existing.fish_caught + new_result.fish_caught
                total_fish_escaped = existing.fish_escaped + new_result.fish_escaped
                
                # Combine rarity breakdowns
                combined_rarity = existing.rarity_breakdown.copy()
                for rarity, count in new_result.rarity_breakdown.items():
                    combined_rarity[rarity] = combined_rarity.get(rarity, 0) + count
                
                # Calculate new metrics
                net_profit = total_revenue - total_investment
                roi_percentage = (net_profit / total_investment * 100) if total_investment > 0 else 0
                avg_profit_per_cast = net_profit / total_cycles if total_cycles > 0 else 0
                catch_rate = total_fish_caught / total_cycles if total_cycles > 0 else 0
                
                # Weighted average of fish values
                existing_total_value = existing.avg_fish_value * existing.fish_caught if existing.fish_caught > 0 else 0
                new_total_value = new_result.avg_fish_value * new_result.fish_caught if new_result.fish_caught > 0 else 0
                avg_fish_value = (existing_total_value + new_total_value) / total_fish_caught if total_fish_caught > 0 else 0
                
                combined_result = SimulationResult(
                    bait_name=new_result.bait_name,
                    bait_id=new_result.bait_id,
                    rod_name=new_result.rod_name,
                    rod_id=new_result.rod_id,
                    bait_cost=new_result.bait_cost,
                    cycles=total_cycles,
                    total_investment=total_investment,
                    total_revenue=total_revenue,
                    net_profit=net_profit,
                    roi_percentage=roi_percentage,
                    avg_profit_per_cast=avg_profit_per_cast,
                    fish_caught=total_fish_caught,
                    fish_escaped=total_fish_escaped,
                    catch_rate=catch_rate,
                    rarity_breakdown=combined_rarity,
                    avg_fish_value=avg_fish_value,
                    recommendation=self._generate_recommendation(roi_percentage, avg_profit_per_cast, catch_rate, new_result.bait_cost),
                    timestamp=datetime.now().isoformat()
                )
                
                combined_results.append(combined_result)
                del existing_lookup[key]  # Remove from lookup
            else:
                # New combination
                combined_results.append(new_result)
        
        # Add any remaining existing results that weren't updated
        combined_results.extend(existing_lookup.values())
        
        # Update combined data
        self.combined_data.combined_results = combined_results
        self.combined_data.total_runs += 1
        self.combined_data.total_cycles += sum(r.cycles for r in new_results)
        self.combined_data.last_updated = datetime.now().isoformat()
        
        # Add to run history
        run_info = {
            'run_number': self.combined_data.total_runs,
            'timestamp': datetime.now().isoformat(),
            'cycles_per_combo': new_results[0].cycles if new_results else 0,
            'total_combinations': len(new_results),
            'total_cycles': sum(r.cycles for r in new_results)
        }
        self.combined_data.run_history.append(run_info)
        
        print(f"✅ Combined data updated - Total runs: {self.combined_data.total_runs}, Total cycles: {self.combined_data.total_cycles:,}")
    
    def clear_combined_data(self) -> None:
        """Clear all combined data"""
        self.combined_data = CombinedData(
            total_runs=0,
            total_cycles=0,
            combined_results=[],
            run_history=[],
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        
        # Delete the file
        if self.data_file.exists():
            self.data_file.unlink()
        
        print("✅ All combined data cleared")
    
    def run_loop_test(self, loops: int, cycles_per_combo: int = 1000) -> None:
        """Run multiple simulation loops and combine data"""
        print(f"\n🔄 Starting loop test: {loops} loops, {cycles_per_combo} cycles per combination")
        
        for loop in range(1, loops + 1):
            print(f"\n{'='*60}")
            print(f"LOOP {loop}/{loops}")
            print(f"{'='*60}")
            
            results = self.run_full_simulation(cycles_per_combo)
            self.combine_with_existing_data(results)
            self._save_combined_data()
            
            # Show quick stats
            if self.combined_data.combined_results:
                roi_values = [r.roi_percentage for r in self.combined_data.combined_results]
                avg_roi = statistics.mean(roi_values)
                print(f"📊 Current average ROI: {avg_roi:.1f}%")
        
        print(f"\n🎉 Loop test completed! {loops} loops finished.")
    
    def check_roi_with_combined_data(self) -> None:
        """Check ROI using combined data"""
        if not self.combined_data.combined_results:
            print("❌ No combined data available. Run a simulation first.")
            return
        
        print(f"\n📊 ROI CHECK - Combined Data Analysis")
        print(f"Based on {self.combined_data.total_runs} runs, {self.combined_data.total_cycles:,} total cycles")
        print("=" * 80)
        
        self.analyze_results(self.combined_data.combined_results)
    
    def show_data_summary(self) -> None:
        """Show summary of combined data"""
        print(f"\n📈 COMBINED DATA SUMMARY")
        print("-" * 50)
        print(f"Total runs: {self.combined_data.total_runs}")
        print(f"Total cycles: {self.combined_data.total_cycles:,}")
        print(f"Created: {self.combined_data.created_at}")
        print(f"Last updated: {self.combined_data.last_updated}")
        print(f"Combinations tracked: {len(self.combined_data.combined_results)}")
        
        if self.combined_data.run_history:
            print(f"\nRun History:")
            for run in self.combined_data.run_history[-5:]:  # Show last 5 runs
                print(f"  Run {run['run_number']}: {run['total_cycles']:,} cycles ({run['timestamp'][:19]})")
            
            if len(self.combined_data.run_history) > 5:
                print(f"  ... and {len(self.combined_data.run_history) - 5} more runs")
        
        if self.combined_data.combined_results:
            roi_values = [r.roi_percentage for r in self.combined_data.combined_results]
            print(f"\nQuick Stats:")
            print(f"  Average ROI: {statistics.mean(roi_values):.1f}%")
            print(f"  Median ROI: {statistics.median(roi_values):.1f}%")
            print(f"  ROI Range: {min(roi_values):.1f}% to {max(roi_values):.1f}%")
    
    def analyze_results(self, results: List[SimulationResult]):
        """Analyze and display simulation results"""
        print("\n" + "=" * 100)
        print("FISHING ECONOMY ANALYSIS RESULTS")
        print("=" * 100)
        
        # Sort results by ROI
        results.sort(key=lambda x: x.roi_percentage, reverse=True)
        
        print(f"\n📊 SUMMARY STATISTICS")
        print("-" * 50)
        roi_values = [r.roi_percentage for r in results]
        profit_values = [r.avg_profit_per_cast for r in results]
        
        print(f"Average ROI: {statistics.mean(roi_values):.1f}%")
        print(f"Median ROI: {statistics.median(roi_values):.1f}%")
        print(f"ROI Range: {min(roi_values):.1f}% to {max(roi_values):.1f}%")
        print(f"Average Profit per Cast: {statistics.mean(profit_values):.1f}")
        
        # Top performers
        print(f"\n🏆 TOP 10 MOST PROFITABLE COMBINATIONS")
        print("-" * 80)
        print(f"{'Rank':<4} {'Bait':<20} {'Rod':<20} {'ROI%':<8} {'Profit/Cast':<12} {'Status'}")
        print("-" * 80)
        
        for i, result in enumerate(results[:10], 1):
            print(f"{i:<4} {result.bait_name[:19]:<20} {result.rod_name[:19]:<20} {result.roi_percentage:<8.1f} {result.avg_profit_per_cast:<12.1f} {result.recommendation}")
        
        # Problem combinations
        overpowered = [r for r in results if r.roi_percentage > 200]
        underpowered = [r for r in results if r.roi_percentage < 0]
        
        if overpowered:
            print(f"\n⚠️  OVERPOWERED COMBINATIONS ({len(overpowered)} total)")
            print("-" * 80)
            for result in overpowered[:5]:  # Show top 5 OP
                print(f"• {result.bait_name} + {result.rod_name}: {result.roi_percentage:.1f}% ROI")
                print(f"  Investment: {result.total_investment:,}, Revenue: {result.total_revenue:,}, Profit: {result.net_profit:,}")
                print(f"  Recommendation: {result.recommendation}\n")
        
        if underpowered:
            print(f"\n🔻 UNDERPOWERED COMBINATIONS ({len(underpowered)} total)")
            print("-" * 80)
            for result in sorted(underpowered, key=lambda x: x.roi_percentage)[:5]:  # Show worst 5
                print(f"• {result.bait_name} + {result.rod_name}: {result.roi_percentage:.1f}% ROI")
                print(f"  Investment: {result.total_investment:,}, Revenue: {result.total_revenue:,}, Loss: {abs(result.net_profit):,}")
                print(f"  Recommendation: {result.recommendation}\n")
        
        # Bait analysis
        print(f"\n🪱 BAIT PERFORMANCE ANALYSIS")
        print("-" * 60)
        bait_performance = {}
        for result in results:
            bait_id = result.bait_id
            if bait_id not in bait_performance:
                bait_performance[bait_id] = []
            bait_performance[bait_id].append(result.roi_percentage)
        
        bait_avg_roi = {bait_id: statistics.mean(rois) for bait_id, rois in bait_performance.items()}
        sorted_baits = sorted(bait_avg_roi.items(), key=lambda x: x[1], reverse=True)
        
        for bait_id, avg_roi in sorted_baits:
            bait_name = self.bait_data[bait_id].get('name', bait_id)
            cost = self.bait_costs.get(bait_id, 0)
            print(f"{bait_name:<25} | Avg ROI: {avg_roi:>7.1f}% | Cost: {cost:>4}")
        
        # Rod analysis
        print(f"\n🎣 ROD PERFORMANCE ANALYSIS")
        print("-" * 60)
        rod_performance = {}
        for result in results:
            rod_id = result.rod_id
            if rod_id not in rod_performance:
                rod_performance[rod_id] = []
            rod_performance[rod_id].append(result.roi_percentage)
        
        rod_avg_roi = {rod_id: statistics.mean(rois) for rod_id, rois in rod_performance.items()}
        sorted_rods = sorted(rod_avg_roi.items(), key=lambda x: x[1], reverse=True)
        
        for rod_id, avg_roi in sorted_rods:
            rod_name = self.rod_data[rod_id].get('name', rod_id)
            multiplier = self.rod_data[rod_id].get('multiplier', 1.0)
            print(f"{rod_name:<25} | Avg ROI: {avg_roi:>7.1f}% | Multiplier: {multiplier:>6.1f}x")
        
        # Save detailed results to file
        self._save_detailed_results(results)
    
    def _save_detailed_results(self, results: List[SimulationResult], append_mode: bool = False):
        """Save detailed results to a JSON file"""
        output_data = []
        for result in results:
            output_data.append({
                'bait_name': result.bait_name,
                'bait_id': result.bait_id,
                'rod_name': result.rod_name,
                'rod_id': result.rod_id,
                'bait_cost': result.bait_cost,
                'cycles': result.cycles,
                'total_investment': result.total_investment,
                'total_revenue': result.total_revenue,
                'net_profit': result.net_profit,
                'roi_percentage': result.roi_percentage,
                'avg_profit_per_cast': result.avg_profit_per_cast,
                'fish_caught': result.fish_caught,
                'fish_escaped': result.fish_escaped,
                'catch_rate': result.catch_rate,
                'rarity_breakdown': result.rarity_breakdown,
                'avg_fish_value': result.avg_fish_value,
                'recommendation': result.recommendation,
                'timestamp': self._get_timestamp()
            })
        
        output_file = 'fishing_simulation_results.json'
        
        if append_mode and os.path.exists(output_file):
            # Load existing data and combine
            try:
                with open(output_file, 'r') as f:
                    existing_data = json.load(f)
                if isinstance(existing_data, list):
                    output_data = existing_data + output_data
            except Exception as e:
                print(f"Warning: Could not load existing data: {e}")
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file} ({'appended' if append_mode else 'overwritten'})")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string"""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def load_existing_results(self) -> List[dict]:
        """Load existing simulation results from file"""
        output_file = 'fishing_simulation_results.json'
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    data = json.load(f)
                return data if isinstance(data, list) else []
            except Exception as e:
                print(f"Error loading existing results: {e}")
                return []
        return []
    
    def clear_simulation_data(self):
        """Clear all stored simulation data"""
        output_file = 'fishing_simulation_results.json'
        try:
            if os.path.exists(output_file):
                os.remove(output_file)
                print("✅ Simulation data cleared successfully!")
            else:
                print("ℹ️  No simulation data file found to clear.")
        except Exception as e:
            print(f"❌ Error clearing data: {e}")
    
    def analyze_combined_results(self, current_results: List[SimulationResult]):
        """Analyze current results combined with historical data"""
        print("\n" + "=" * 100)
        print("COMBINED DATASET ANALYSIS (Current + Historical)")
        print("=" * 100)
        
        # Load historical data
        historical_data = self.load_existing_results()
        
        # Convert current results to dict format
        current_data = []
        for result in current_results:
            current_data.append({
                'bait_name': result.bait_name,
                'bait_id': result.bait_id,
                'rod_name': result.rod_name,
                'rod_id': result.rod_id,
                'roi_percentage': result.roi_percentage,
                'avg_profit_per_cast': result.avg_profit_per_cast,
                'cycles': result.cycles,
                'recommendation': result.recommendation,
                'timestamp': self._get_timestamp()
            })
        
        # Combine datasets
        all_data = historical_data + current_data
        
        if not all_data:
            print("No data available for analysis.")
            return
        
        print(f"📊 DATASET OVERVIEW")
        print(f"Historical runs: {len(historical_data)}")
        print(f"Current run: {len(current_data)}")
        print(f"Total combinations: {len(all_data)}")
        
        # Group by combination and analyze trends
        combination_trends = {}
        for entry in all_data:
            key = f"{entry['bait_id']}_{entry['rod_id']}"
            if key not in combination_trends:
                combination_trends[key] = {
                    'bait_name': entry['bait_name'],
                    'rod_name': entry['rod_name'],
                    'roi_values': [],
                    'profit_values': [],
                    'runs': 0
                }
            combination_trends[key]['roi_values'].append(entry['roi_percentage'])
            combination_trends[key]['profit_values'].append(entry['avg_profit_per_cast'])
            combination_trends[key]['runs'] += 1
        
        # Find most tested combinations
        print(f"\n🔬 MOST TESTED COMBINATIONS")
        print("-" * 80)
        sorted_by_runs = sorted(combination_trends.items(), key=lambda x: x[1]['runs'], reverse=True)
        for i, (key, data) in enumerate(sorted_by_runs[:10], 1):
            avg_roi = statistics.mean(data['roi_values'])
            roi_std = statistics.stdev(data['roi_values']) if len(data['roi_values']) > 1 else 0
            print(f"{i:2}. {data['bait_name']} + {data['rod_name']}")
            print(f"    Runs: {data['runs']}, Avg ROI: {avg_roi:.1f}% (±{roi_std:.1f}%)")
        
        # Overall statistics
        all_roi_values = [entry['roi_percentage'] for entry in all_data]
        print(f"\n📈 OVERALL STATISTICS")
        print("-" * 50)
        print(f"Total data points: {len(all_roi_values)}")
        print(f"Average ROI: {statistics.mean(all_roi_values):.1f}%")
        print(f"Median ROI: {statistics.median(all_roi_values):.1f}%")
        print(f"ROI Standard Deviation: {statistics.stdev(all_roi_values):.1f}%")
        print(f"ROI Range: {min(all_roi_values):.1f}% to {max(all_roi_values):.1f}%")
        
        # Problem combinations (consistent across runs)
        overpowered_consistent = []
        for key, data in combination_trends.items():
            if len(data['roi_values']) >= 2:  # At least 2 runs
                avg_roi = statistics.mean(data['roi_values'])
                if avg_roi > 200:  # Consistently overpowered
                    overpowered_consistent.append((key, data, avg_roi))
        
        if overpowered_consistent:
            print(f"\n⚠️  CONSISTENTLY OVERPOWERED COMBINATIONS")
            print("-" * 80)
            overpowered_consistent.sort(key=lambda x: x[2], reverse=True)
            for key, data, avg_roi in overpowered_consistent[:10]:
                roi_std = statistics.stdev(data['roi_values']) if len(data['roi_values']) > 1 else 0
                print(f"• {data['bait_name']} + {data['rod_name']}")
                print(f"  Avg ROI: {avg_roi:.1f}% (±{roi_std:.1f}%) over {data['runs']} runs")
    
    def run_loop_simulation(self, loops: int):
        """Run simulation multiple times in loops"""
        print(f"\n🔄 STARTING LOOP SIMULATION ({loops} loops)")
        print("=" * 80)
        
        all_loop_results = []
        
        for loop_num in range(1, loops + 1):
            print(f"\n--- Loop {loop_num}/{loops} ---")
            results = self.run_full_simulation()
            all_loop_results.extend(results)
            
            # Save after each loop (append mode)
            self._save_detailed_results(results, append_mode=True)
            
            print(f"Loop {loop_num} completed. Results appended to dataset.")
        
        print(f"\n✅ All {loops} loops completed!")
        print(f"Total simulation runs: {len(all_loop_results)}")
        
        # Analyze the loop results
        print("\n" + "=" * 100)
        print("LOOP SIMULATION ANALYSIS")
        print("=" * 100)
        
        # Group results by combination across loops
        combination_stats = {}
        for result in all_loop_results:
            key = f"{result.bait_id}_{result.rod_id}"
            if key not in combination_stats:
                combination_stats[key] = {
                    'bait_name': result.bait_name,
                    'rod_name': result.rod_name,
                    'roi_values': [],
                    'profit_values': []
                }
            combination_stats[key]['roi_values'].append(result.roi_percentage)
            combination_stats[key]['profit_values'].append(result.avg_profit_per_cast)
        
        # Find most consistent performers
        consistent_performers = []
        for key, data in combination_stats.items():
            if len(data['roi_values']) >= loops:  # Has data from all loops
                avg_roi = statistics.mean(data['roi_values'])
                roi_std = statistics.stdev(data['roi_values']) if len(data['roi_values']) > 1 else 0
                consistency_score = avg_roi / (roi_std + 1)  # Higher is more consistent
                consistent_performers.append((key, data, avg_roi, roi_std, consistency_score))
        
        print(f"\n🎯 MOST CONSISTENT HIGH PERFORMERS (across {loops} loops)")
        print("-" * 80)
        consistent_performers.sort(key=lambda x: x[4], reverse=True)  # Sort by consistency score
        
        for i, (key, data, avg_roi, roi_std, consistency) in enumerate(consistent_performers[:10], 1):
            if avg_roi > 100:  # Only show profitable ones
                print(f"{i:2}. {data['bait_name']} + {data['rod_name']}")
                print(f"    Avg ROI: {avg_roi:.1f}% (±{roi_std:.1f}%) | Consistency Score: {consistency:.1f}")
        
        return all_loop_results

    def export_balance_recommendations(self, results: List[SimulationResult]):
        """Export balance recommendations to a text file"""
        output_file = 'fishing_balance_recommendations.txt'
        
        # Sort results by ROI
        results.sort(key=lambda x: x.roi_percentage, reverse=True)
        
        with open(output_file, 'w') as f:
            f.write("FISHING ECONOMY BALANCE RECOMMENDATIONS\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total combinations analyzed: {len(results)}\n\n")
            
            # Summary statistics
            roi_values = [r.roi_percentage for r in results]
            f.write("SUMMARY STATISTICS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Average ROI: {statistics.mean(roi_values):.1f}%\n")
            f.write(f"Median ROI: {statistics.median(roi_values):.1f}%\n")
            f.write(f"ROI Range: {min(roi_values):.1f}% to {max(roi_values):.1f}%\n\n")
            
            # Critical fixes needed
            critical = [r for r in results if r.roi_percentage > 500]
            overpowered = [r for r in results if 200 < r.roi_percentage <= 500]
            underpowered = [r for r in results if r.roi_percentage < 0]
            
            f.write("CRITICAL BALANCE ISSUES (500%+ ROI)\n")
            f.write("-" * 40 + "\n")
            if critical:
                for result in critical[:10]:  # Top 10 critical
                    f.write(f"• {result.bait_name} + {result.rod_name}: {result.roi_percentage:.1f}% ROI\n")
                    f.write(f"  {result.recommendation}\n\n")
            else:
                f.write("None found\n\n")
            
            f.write("OVERPOWERED COMBINATIONS (200-500% ROI)\n")
            f.write("-" * 40 + "\n")
            if overpowered:
                f.write(f"Total overpowered combinations: {len(overpowered)}\n")
                for result in overpowered[:10]:  # Top 10 overpowered
                    f.write(f"• {result.bait_name} + {result.rod_name}: {result.roi_percentage:.1f}% ROI\n")
            else:
                f.write("None found\n")
            f.write("\n")
            
            f.write("UNDERPOWERED COMBINATIONS (Negative ROI)\n")
            f.write("-" * 40 + "\n")
            if underpowered:
                f.write(f"Total underpowered combinations: {len(underpowered)}\n")
                for result in sorted(underpowered, key=lambda x: x.roi_percentage)[:10]:
                    f.write(f"• {result.bait_name} + {result.rod_name}: {result.roi_percentage:.1f}% ROI\n")
            else:
                f.write("None found\n")
            f.write("\n")
            
            # Bait analysis
            f.write("BAIT PERFORMANCE ANALYSIS\n")
            f.write("-" * 40 + "\n")
            bait_performance = {}
            for result in results:
                bait_id = result.bait_id
                if bait_id not in bait_performance:
                    bait_performance[bait_id] = []
                bait_performance[bait_id].append(result.roi_percentage)
            
            bait_avg_roi = {bait_id: statistics.mean(rois) for bait_id, rois in bait_performance.items()}
            sorted_baits = sorted(bait_avg_roi.items(), key=lambda x: x[1], reverse=True)
            
            for bait_id, avg_roi in sorted_baits:
                bait_name = self.bait_data[bait_id].get('name', bait_id)
                cost = self.bait_costs.get(bait_id, 0)
                f.write(f"{bait_name:<25} | Avg ROI: {avg_roi:>7.1f}% | Cost: {cost:>4}\n")
            f.write("\n")
            
            # Rod analysis
            f.write("ROD PERFORMANCE ANALYSIS\n")
            f.write("-" * 40 + "\n")
            rod_performance = {}
            for result in results:
                rod_id = result.rod_id
                if rod_id not in rod_performance:
                    rod_performance[rod_id] = []
                rod_performance[rod_id].append(result.roi_percentage)
            
            rod_avg_roi = {rod_id: statistics.mean(rois) for rod_id, rois in rod_performance.items()}
            sorted_rods = sorted(rod_avg_roi.items(), key=lambda x: x[1], reverse=True)
            
            for rod_id, avg_roi in sorted_rods:
                rod_name = self.rod_data[rod_id].get('name', rod_id)
                multiplier = self.rod_data[rod_id].get('multiplier', 1.0)
                f.write(f"{rod_name:<25} | Avg ROI: {avg_roi:>7.1f}% | Multiplier: {multiplier:>6.1f}x\n")
            f.write("\n")
            
            # Top 20 most profitable
            f.write("TOP 20 MOST PROFITABLE COMBINATIONS\n")
            f.write("-" * 40 + "\n")
            for i, result in enumerate(results[:20], 1):
                f.write(f"{i:2}. {result.bait_name} + {result.rod_name}\n")
                f.write(f"    ROI: {result.roi_percentage:.1f}% | Profit/Cast: {result.avg_profit_per_cast:.1f}\n")
                f.write(f"    {result.recommendation}\n\n")
        
        print(f"\n📋 Balance recommendations exported to: {output_file}")

def show_menu():
    """Display the main menu"""
    print("\n" + "="*60)
    print("🎣 FISHING ECONOMY SIMULATION SUITE")
    print("="*60)
    print("1. 📊 Check ROI (run simulation & combine with existing data)")
    print("2. 🔄 Loop Check (run multiple simulation loops)")  
    print("3. 🗑️  Clear Data (reset all combined data)")
    print("4. 📈 Show Data Summary (view current combined data stats)")
    print("5. 💾 Export Results (save current results to file)")
    print("6. ⚙️  Quick Single Test (test specific bait/rod combination)")
    print("7. 🔍 Compare Combinations (compare specific bait/rod pairs)")
    print("8. 📋 Balance Recommendations (show balance suggestions)")
    print("9. ❓ Help (show detailed information)")
    print("0. 🚪 Exit")
    print("-"*60)

def get_user_input(prompt: str, input_type: type = str, min_val: int = None, max_val: int = None):
    """Get validated user input"""
    while True:
        try:
            value = input_type(input(prompt))
            if input_type == int and min_val is not None and value < min_val:
                print(f"❌ Value must be at least {min_val}")
                continue
            if input_type == int and max_val is not None and value > max_val:
                print(f"❌ Value must be at most {max_val}")
                continue
            return value
        except ValueError:
            print(f"❌ Invalid input. Please enter a valid {input_type.__name__}")

def quick_single_test(simulator: FishingSimulator):
    """Test a specific bait/rod combination"""
    print("\n🔬 QUICK SINGLE TEST")
    print("-" * 30)
    
    # Show available baits
    print("\nAvailable Baits:")
    bait_list = list(simulator.bait_data.keys())
    for i, bait_id in enumerate(bait_list[:10], 1):  # Show first 10
        bait_name = simulator.bait_data[bait_id].get('name', bait_id)
        cost = simulator.bait_costs.get(bait_id, 0)
        print(f"  {i:2}. {bait_name} ({bait_id}) - {cost:,} cost")
    
    if len(bait_list) > 10:
        print(f"  ... and {len(bait_list) - 10} more baits")
    
    bait_id = input("\nEnter bait ID: ").strip()
    if bait_id not in simulator.bait_data:
        print(f"❌ Bait '{bait_id}' not found")
        return
    
    # Show available rods
    print("\nAvailable Rods:")
    rod_list = list(simulator.rod_data.keys())
    for i, rod_id in enumerate(rod_list[:10], 1):  # Show first 10
        rod_name = simulator.rod_data[rod_id].get('name', rod_id)
        multiplier = simulator.rod_data[rod_id].get('multiplier', 1.0)
        print(f"  {i:2}. {rod_name} ({rod_id}) - {multiplier:.1f}x multiplier")
    
    if len(rod_list) > 10:
        print(f"  ... and {len(rod_list) - 10} more rods")
    
    rod_id = input("\nEnter rod ID: ").strip()
    if rod_id not in simulator.rod_data:
        print(f"❌ Rod '{rod_id}' not found")
        return
    
    cycles = get_user_input("Enter number of cycles (default 1000): ", int, 1, 100000)
    if not cycles:
        cycles = 1000
    
    print(f"\n🎣 Testing {bait_id} + {rod_id} for {cycles} cycles...")
    result = simulator.simulate_bait_rod_combination(bait_id, rod_id, cycles)
    
    print(f"\n📊 RESULTS:")
    print(f"Investment: {result.total_investment:,}")
    print(f"Revenue: {result.total_revenue:,}")
    print(f"Profit: {result.net_profit:,}")
    print(f"ROI: {result.roi_percentage:.1f}%")
    print(f"Fish caught: {result.fish_caught}/{cycles} ({result.catch_rate:.1%})")
    print(f"Average profit per cast: {result.avg_profit_per_cast:.1f}")
    print(f"Recommendation: {result.recommendation}")
    
    if result.rarity_breakdown:
        print(f"\nRarity Breakdown:")
        for rarity, count in sorted(result.rarity_breakdown.items(), key=lambda x: x[1], reverse=True):
            print(f"  {rarity}: {count} fish")

def export_results(simulator: FishingSimulator):
    """Export current results to file"""
    if not simulator.combined_data.combined_results:
        print("❌ No data to export")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_file = f"/fishing_export_{timestamp}.json"
    
    try:
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'total_runs': simulator.combined_data.total_runs,
                'total_cycles': simulator.combined_data.total_cycles,
                'combinations': len(simulator.combined_data.combined_results)
            },
            'summary_stats': {
                'avg_roi': statistics.mean([r.roi_percentage for r in simulator.combined_data.combined_results]),
                'median_roi': statistics.median([r.roi_percentage for r in simulator.combined_data.combined_results]),
                'min_roi': min([r.roi_percentage for r in simulator.combined_data.combined_results]),
                'max_roi': max([r.roi_percentage for r in simulator.combined_data.combined_results])
            },
            'results': [
                {
                    'bait_name': r.bait_name,
                    'bait_id': r.bait_id,
                    'rod_name': r.rod_name,
                    'rod_id': r.rod_id,
                    'cycles': r.cycles,
                    'roi_percentage': r.roi_percentage,
                    'avg_profit_per_cast': r.avg_profit_per_cast,
                    'catch_rate': r.catch_rate,
                    'recommendation': r.recommendation
                } for r in sorted(simulator.combined_data.combined_results, key=lambda x: x.roi_percentage, reverse=True)
            ],
            'run_history': simulator.combined_data.run_history
        }
        
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✅ Results exported to {export_file}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")

def show_help():
    """Show detailed help information"""
    print("\n📚 HELP - FISHING SIMULATION SUITE")
    print("="*50)
    print("""
🎯 PURPOSE:
This tool helps balance the fishing economy by simulating thousands of 
fishing cycles and analyzing profitability (ROI).

📊 MENU OPTIONS:

1. CHECK ROI: Runs a full simulation (all bait/rod combinations) and 
   combines results with existing data. Shows comprehensive analysis.

2. LOOP CHECK: Runs multiple simulation rounds in sequence. Useful for
   getting more accurate averages and testing consistency.

3. CLEAR DATA: Resets all accumulated data. Use this when you've updated
   bait/rod values and want fresh testing.

4. SHOW DATA SUMMARY: View statistics about your accumulated test data
   without running new simulations.

5. EXPORT RESULTS: Save current results to a timestamped JSON file for
   external analysis or record keeping.

6. QUICK SINGLE TEST: Test one specific bait/rod combination quickly
   instead of running the full simulation.

7. COMPARE COMBINATIONS: [Feature for comparing specific pairs]

8. BALANCE RECOMMENDATIONS: Shows specific suggestions for nerfing/buffing
   based on current data.

📈 UNDERSTANDING ROI:
- 50-100% ROI: Balanced, good profit potential
- 100-200% ROI: Slightly overpowered, minor nerfs needed  
- 200-500% ROI: Overpowered, significant nerfs needed
- 500%+ ROI: Severely overpowered, major nerfs required
- Negative ROI: Underpowered, buffs needed

🔄 DATA PERSISTENCE:
All simulation results are automatically saved and combined across sessions.
This allows you to build up large datasets for more accurate analysis.

⚙️ TECHNICAL NOTES:
- Each simulation tests all possible bait/rod combinations
- Default is 1000 cycles per combination (840 combos = 840,000 total cycles)
- Rod durability, fish escape chances, and all game mechanics are simulated
- Results include detailed breakdowns by rarity, catch rates, and profitability
""")

def main_interactive():
    """Main interactive function with menu system"""
    print("🎣 FISHING ECONOMY SIMULATION SUITE")
    print("Initializing...")
    
    try:
        simulator = FishingSimulator()
    except Exception as e:
        print(f"❌ Failed to initialize simulator: {e}")
        return
    
    while True:
        show_menu()
        
        try:
            choice = input("Enter your choice (0-9): ").strip()
            
            if choice == "0":
                print("\n👋 Goodbye! Data has been saved.")
                break
                
            elif choice == "1":
                # Check ROI
                cycles = get_user_input("\nEnter cycles per combination (default 1000): ", int, 1, 100000)
                if not cycles:
                    cycles = 1000
                
                print(f"\n🎯 Running full simulation with {cycles} cycles per combination...")
                results = simulator.run_full_simulation(cycles)
                simulator.combine_with_existing_data(results)
                simulator._save_combined_data()
                simulator.check_roi_with_combined_data()
                
            elif choice == "2":
                # Loop Check
                loops = get_user_input("\nEnter number of loops: ", int, 1, 100)
                cycles = get_user_input("Enter cycles per combination (default 1000): ", int, 1, 100000)
                if not cycles:
                    cycles = 1000
                
                simulator.run_loop_test(loops, cycles)
                
            elif choice == "3":
                # Clear Data
                confirm = input("\n⚠️  Are you sure you want to clear ALL data? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y']:
                    simulator.clear_combined_data()
                else:
                    print("❌ Clear cancelled")
                    
            elif choice == "4":
                # Show Data Summary
                simulator.show_data_summary()
                
            elif choice == "5":
                # Export Results
                export_results(simulator)
                
            elif choice == "6":
                # Quick Single Test
                quick_single_test(simulator)
                
            elif choice == "7":
                # Compare Combinations (placeholder)
                print("🚧 Feature coming soon!")
                
            elif choice == "8":
                # Balance Recommendations
                if simulator.combined_data.combined_results:
                    simulator.check_roi_with_combined_data()
                else:
                    print("❌ No data available. Run a simulation first.")
                    
            elif choice == "9":
                # Help
                show_help()
                
            else:
                print("❌ Invalid choice. Please enter 0-9.")
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Continuing...")
        
        # Pause before showing menu again
        if choice not in ["0", "9"]:  # Don't pause for exit or help
            input("\n📝 Press Enter to continue...")

def main():
    """Main function - now just calls the interactive version"""
    main_interactive()

if __name__ == "__main__":
    main()
