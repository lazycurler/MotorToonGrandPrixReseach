After hearing about the lap skip I was interested in learning more about the respawn mechanics and took some time over the past few weeks to reverse engineer relevant parts of the code. While I by no means have a perfect understanding of all the underlying mechanics (they are surprisingly complex and have many edge cases), I hope to provide some insight into how these tricks work and formalize the concepts that were previously discovered. 


# Respawn Mechanics
In general, all of the above tricks revolve around controlling a piece of memory I've been calling Respawn Track Progress or `respawnTrackProg`. It's not a catchy name, but it'll hopefully make more sense why I picked that name in a bit. It's job is to keep track of the last valid location the players car was at on a given track. Notably, it does not update while the car is off the track. Critically, this includes both off the track **and** in the air _over_ the track. When a car needs to be respawned this is the value that is used to determine (indirectly) where the car is suppose to be placed back on the track. While I have not completely decompiled this section of code, the jist of it is `respawnTrackProg` is used to lookup the next spawn point in a list of spawn points. This means cases of forward warping are usually just being at the beginning of section/chunk and being placed towards the end, but not always.


# Corkscrew Skip
This is actually an interesting case of forward warping due to some buggy terrain. While normally driving on a railing wouldn't update the respawn position, that is not the case here. In this specific area, if the car is maneuvered just so, the game thinks the car is on valid terrain and updates the respawn track progress. The car's position (according to the game) is thought to be off to the right just about where the exit off the corkscrew is before the ramp back up. Thus, when the respawn is triggered it uses that bottom of the corkscrew position to calculate where to respawn and moves the car even further along the track.


# Tracking the Car's Progress
Now, before I talk about how/why lap skip works. I need to introduce two more pieces of memory: `currTrackProg` and `prevTrackProg`. These two values represent the cars current and previous progression on the race track. Their values range from `0` just after the finish line to some high number (that is track specific) right before the finish line. These values are updated whenever the car is on or **above** the track (unlike `respawnTrackProg`). Every time the position of the car is updated (aka every tick) `prevTrackProg` gets updated to be what `currTrackProg` was and `currTrackProg` is then updated to be the newly calculated value. In this way, the game can keep track of how the player is progressing on the track, determine if they are going forwards (`curr > prev`), backwards (`curr < prev`), and crucially: determine when a lap has been completed.


# Completing a Lap
Before being able to determine if a car has finished a lap, two more additional pieces of information (arguably only one) are needed; the position of the finish line and the halfway point. The finish line is unique to each track and stored in units matching those of `[curr,prev]TrackProg`. The halfway point's position is then derived from the finish lines. It is simply the finish line's position divided by two (technically bit shifted right by one). While the finish line's point is helpful to know, the game uses only the halfway point, combined with the cars current and previous track progress, to determine if a lap has been completed. The checkpoint marked in-game is used only for displaying in-progress lap splits (or similar) and not technically needed to be crossed (on the track) to finish a lap.

As mentioned above, every tick the current and previous position of the car are updated and checked, the game then determines if the car is moving forwards or backwards, and if a lap has been completed. Ignoring the edge cases and minutia the critical check for a laps completion is as follows:

**Nominal Finish Line Crossing**
1. `currTrackProg < prevTrackProg`
2. `(currentTrackProg + halfwayPoint) < prevTrackProg`

Or in simple/general terms, the car's new position on the track must be **much less** (more than half a track) than its previous position (in a single tick) for a lap to be counted. However, in opposition to the above check, to cross the finish line the _wrong_ way the following checks must be satisfied:

**Wrong-Way Finish Line Crossing**
1. `currTrackProg >= prevTrackProg`
2. `(prevTrackProg + halfwayPoint) < currTrackProg`

Again, put simply this would mean the cars current track position is suddenly **much greater** (more than half a track) than it's previous position (in a single tick). This flips the internal lap counter negative and the only way to undo this is to complete a nominal finish line crossing. Note, if the internal lap count is `0` no update occurs and the count remains `0`.

# Lap Skip
Using the knowledge and mechanics above, a lap skip can be performed. Lap skips are really just forward warping, or respawning so far forward that the game believes you have crossed the finish line, but not so far as to trigger the games wrong-way detection. The setup for a long forward warp/lap skip is as follows:
1. Drive on the road like a normal player 
	* This sets the `respawnTrackProg`
2. Start driving off-road (non-road terrain/jumping in air)
	* This continues to update `currTrackProg` and `prevTrackProg`
	* This does _not_ update `respawnTrackProg`
	* The beach on Toon Island II is considered track/road
3. Continue driving off-road until the car is more than half a track away from the previously set respawn point
4. Trigger a respawn
	* Run into the ocean, go out of bounds, etc

# Forward Warping Diagram
This image shows the maximum possible lap skip distance (~half a track) and shows some example of the above calculations.
https://i.imgur.com/t8AoyIg.png


I hope this proves useful, or at the very least entertaining. I had a lot of fun digging through the code to figure all this out. If anyone is interested in doing some exploit hunting I can post track lengths along with other relevant memory addresses. For map exploration, I've found that freezing the item memory address `0x800DC3CB` with the jump item `0x04` makes moving around the map extremely easy. Any questions or suggestions (for this game and others) are welcome!