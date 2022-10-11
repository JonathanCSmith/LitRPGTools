## TODO:
* Assess feasibility of doing a full systemic state simulation
* Event based updating of categories?
* Dynamic category scaling (Quests)
* State dependent category metas (Inventory size)
* Data replication
* Spell checking package for GUI
* Support for bullet points
* Up/Down key navigation in history list doesnt update GUI
* Smarter GUI Updating
* Delete {property}
* Search and replace?
* Category name & list entry styling cannot be None
* If it's an update, show before + current on 'selected'
* Re-evaluate whether our try catch on data_value get (where cat length doesnt match) is necessary any more
* Bug where load big file, load small file, history index > allowed for small file

##### Sprints:
```
deconvolve:
    print to output
    print to history
    notes only

    targets:
        should be in history
        should be in overview
        should only be in GUI

THINK about a dynamic properties system:
    global registry
    all 'entries' can have dynamic effects, categories can set common effects, effects are 'triggerable (don't update history?)'
        downside to this plan is it doesnt auto add entries, but that may be fine
    text 'lookup' function on {} (Can pull from global registry)
```

### Problem Children for full state conversion:
* Score manipulations are order dependent (if mix of additions and multiplications)
* Non secondary calculations - i.e. values dependent on values depenedent on values

### Implementation
* Thought process:
  * Declare view, declare modification events, declare externally available variables
  * User Story - Levels:
    * State
      * View == Current XP, Required XP, Total XP, Total Required XP, Current Level
      * Events == XP Up, XP Down
      * Externally available == Total XP, XP Increase, XP Decrease, XP % Increase, XP % Decrease
    * To Create:
      1) Select 'Create View'
      2) Choose Singleton
      3) Add field headings
      4) Add field values
         * Needs to consider calculations somehow. For ex: Level == Lookup Current Total - Run though level calc
      5) Add in statically declared fields. 
  * User Story - Wis dependent tertiary stat:
  * User Story - :

## New Version:
* Full dynamic data implementation
  * Track all actions
  * Save data needs to 100% Replicate entries.
  * Entries need to 'watch' variables and dynamically update 
  * Chained create an entry - this need not be tracked in the save data
  * Deletion/Editing needs to be aware.

## What do I actually want
1) Better clarity on display toggling
2) Dynamic value tracking and injection into views
3) Dynamic event triggering based on dynamic value editing 
4) Spell checking
5) Bullet points
6) Find, Find & Replace
7) Entry shows before & current & after? Or have button navigation?
8) Possibly switch to deltas? 
9) Better notifications when things are wrong
10) Better history log text
11) Come up with a mechanism that ensures updated entries (via dynamic data) is displayed in gsheets when desired.
12) Code clean up
13) Categories are versionable

#### CURRENTLY UNDERWAY CHARACTER != CATEGORY
Delete character relocate
handle_update_menus -> delete character change in MainGUI

### DONE
1) Categories are global but toggleable per entity.