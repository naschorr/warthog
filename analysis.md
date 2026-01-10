# Replay Data Explorer Analysis

## Introduction

War Thunder often doesn't *feel* very fair. Once you've learn about using the spawn point cost for your vehicles to determine where the matchmaker placed you, it can start to feel like you [never really had a chance](https://youtu.be/s-1WxfsJzPM?t=43).

<img src="https://github.com/naschorr/warthog/blob/main/output/graphs/scatter_score_vs_br.png?raw=true">

This is a graph of score versus battle rating for every recorded match that I've played. Nodes are colored to show how my battle rating compares to the match's (see [Uptiers and Downtiers](#uptiers-and-downtiers) for more information about battle rating tiers). There's a trendline of my performance as I progress into further tiers, but it's pretty clear what's happening even without it. The big question is why?

There's a few ideas floating around:

1. The first (and maybe most likely) is just that I'm not that good. Lower tiers have newer players, and with how grindy War Thunder is, the folks that were padding my stats never made it to the higher battle ratings.

2. The second is simply game design. Vehicle upgrades get more and more expensive as you go up in the battle ratings, which means that the absolute basics (like repair kits, or fire extinguishers) are locked behind higher and higher research point requirements. You end up having less survivability, less maneuverability, worse ammunition, which makes getting the research points to climb out of the hole even harder. (Of course you could always buy a few weeks of premium to speed things up...)

3. Lastly, War Thunder has a [freemium](https://en.wikipedia.org/wiki/Freemium) model. It's free to play, but the developers have to make money somehow, and so they design premium vehicles that range from barely an upgrade over their free counterparts (see: [Strv m/41 S-I](https://wiki.warthunder.com/unit/sw_strv_m41_s1)) to stuff that's really broken and can't be purchased any more (see: [SAV 20.12.48](https://wiki.warthunder.com/unit/sw_sav_fm48)). Could the developers also be tweaking the matchmaker to give preferential treatment to players that purchase premium vehicles to hopefully incentivise even more purchases by folks chasing a dopamine hit?

I'm hoping to explore those ideas (and more) in the sections below, using War Thunder replay data gathered and processed by [Warthog](https://github.com/naschorr/warthog).

## Uptiers and Downtiers

In ground realistic battles, War Thunder tries to group players together into buckets where the vehicles that they use are of a relatively similar skill. These buckets usually span one battle rating (ex: the top end of the match might be 4.3, and the bottom should be 3.3), though if a squad of players enters the match together, the player with the highest battle rating determines the squad's battle rating. If a player's battle rating is at the top of the match, then they are thought of as being "downtiered". Likewise, if a player's battle rating is at the bottom then they're thought of as being "uptiered". To add additional granularity, I've added more breakpoints to better illustrate how the different battle ratings might interact in a match. Here's the breakdown of how a player's battle rating would be classified in a match of battle rating 4.3 (and thus having a floor of 3.3).

- player_battle_rating >= 4.3 -> Downtier
- 4.3 > player_battle_rating > 4.0 -> Partial Downtier
- 4.0 >= player_battle_rating >= 3.6 -> Balanced
- 3.6 > player_battle_rating > 3.3 -> Partial Uptier
- 3.3 >= player_battle_rating -> Uptier

Take a look at War Thunder's [matchmaking docs](https://wiki.warthunder.com/mechanics/matchmaking) for more information.

### Hypothesis

War Thunder matchmaking places me at or near the bottom of the battle rating bucket more often that not.

### Data

<img src="https://github.com/naschorr/warthog/blob/main/output/graphs/pie_tier_frequency.png?raw=true">
A pie chart showing frequency of tiers.
<br>
<br>

<img src="https://github.com/naschorr/warthog/blob/main/output/graphs/bar_tier_distribution.png?raw=true">
A chronological graph showing battle rating deltas (the difference from the match's battle rating midpoint) for all recorded match data. Note that even the majority of "balanced" matches are still slightly skewed in favor of an uptier.
<br>
<br>

<img src="https://github.com/naschorr/warthog/blob/main/output/graphs/bar_tier_frequency_vs_country.png?raw=true">
Tier frequencies for all played countries.
<br>
<br>

<img src="https://github.com/naschorr/warthog/blob/main/output/graphs/bar_tier_frequency_vs_br.png?raw=true">
Tier frequencies for all played played battle ratings.
<br>
<br>

<img src="https://github.com/naschorr/warthog/blob/main/output/graphs/bar_squad_tier_distribution.png?raw=true">
Tier frequencies for all squad sizes

### Conclusion

Throughout all of the available data, I am consistently uptiered or partially uptiered nearly two thirds of the time. The countries with significant data available all demonstrate this, though more data is necessary for the other countries. The battle rating of the match does seem to play a part somewhat, with more favorable matchmaking happening in the 3.7 to 4.7 range. Queueing in a squad doesn't seem to change things either, as the majority of matches are still played in an uptier or partially uptiered situation.

These results would indicate that there's either not a linear distribution of player battle ratings matchmaking with me, the countries that encompass most of my data might have bad battle rating breakpoints when compared to other countries (for example: Sweden has a breakpoint at [5.7](https://wiki.warthunder.com/ground?v=t&t_c=sweden), and Germany has one at [6.7](https://wiki.warthunder.com/ground?v=t&t_c=germany), if many players are queuing up with those battle rating optimized lineups, it makes sense that there would be matchups between them.), or there might simply be a problem with the matchmaking algorithm itself (maybe preferential treatment for folks purchasing premium vehicles and premium currency?)
