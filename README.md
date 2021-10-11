# Athanor - A Barebones MU* Framework for Python

## WARNING: Early Alpha!
Pardon our dust, this project is still in its infancy. It runs, but if you're not a developer intent on sprucing up, it may not have much for you just yet.

## CONTACT INFO
**Name:** Volund

**Email:** volundmush@gmail.com

**PayPal:** volundmush@gmail.com

**Discord:** Volund#1206  

**Discord Channel:** https://discord.gg/Sxuz3QNU8U

**Patreon:** https://www.patreon.com/volund

**Home Repository:** https://github.com/volundmush/athanor

## TERMS AND CONDITIONS

MIT license. In short: go nuts, but give credit where credit is due.

Please see the included LICENSE.txt for the legalese.

## INTRO
MUDs and their brethren are the precursors to our modern MMORPGs, and are still a blast to play - in addition to their other uses, such as educative game design: all the game logic, none of the graphics!

Writing one from scratch isn't easy though, so this library aims to take away a great deal of the boilerplate pain.

Athanor provides a dual-process Application framework and a launcher, where each and every piece of the program is meant to be inherited and overloaded by another developer's efforts. The Portal process holds onto clients and communicates with the Server process over local private networking, allowing the Server to reboot - and apply updates - without disconnecting clients.

This library isn't a MUD. It's not a MUSH, or a MUX, or a MOO, or MUCK on its own, though. In truth, it doesn't DO very much. That's a good thing! See, it doesn't make many decisions for the developers it's meant for, making it easy to build virtually ANY kind of text-based multiplayer game atop of it.

## FEATURES
  * Full Telnet Support (courtesy of the mudtelnet library)
  * Extendable Protocol Framework

## UNFINISHED FEATURES
  * TLS Support
  * WebSocket Support
  * SSH Support
  * Integrated WebClient


## RECOMMENDED LIBRARIES:
  * [mudstring](https://github.com/volundmush/mudstring-python) - do-it-all library for manipulatable, serializable ANSI text that even supports MXP, with all of [rich](https://github.com/willmcgugan/rich) 's pretty-formatting power.

## OKAY, BUT HOW DO I USE IT?
Glad you asked!

You can install athanor using ```pip install athanor```

This adds the `athanor` command to your shell. use `athanor --help` to see what it can do.

The way that athanor and projects built on it work:

`athanor --init <folder>` will create a folder that contains your game's configuration, save files, database, and possibly some code. Enter the folder and use `athanor start` and `athanor stop` to control it. you can use `--app server` or `--app portal` to start/stop specific programs.

Examine the appdata/config.py and portal.py and server.py - which get their initial configuration from mudcano's defaults - for how to change the server's configuration around.

Again, though, it doesn't do much...

## OKAAAAAAY, SO HOW DO I -REALLY- USE IT?
The true power of Athanor is in its extendability. Because you can replace any and all classes the program uses for its startup routines, and the launcher itself is a class, it's easy-peasy to create a whole new library with its own command-based launcher and game template that the launcher creates a skeleton of with `--init <folder>`.

Not gonna lie though - that does need some Python skills.

If you're looking for a project already built on Athanor for you, check out [pymush](https://github.com/volundmush/pymush) and don't let the MUSH in the name fool you - it's built for MUDs too!

## FAQ 
  __Q:__ This is cool! How can I help?  
  __A:__ [Patreon](https://www.patreon.com/volund) support is always welcome. If you can code and have cool ideas or bug fixes, feel free to fork, edit, and pull request! Join our [discord](https://discord.gg/Sxuz3QNU8U) to really get cranking away though.

  __Q:__ I found a bug! What do I do?  
  __A:__ Post it on this GitHub's Issues tracker. I'll see what I can do when I have time. ... or you can try to fix it yourself and submit a Pull Request. That's cool too.

  __Q:__ But... I want a MUD! Where do I start making a MUD?  
  __A:__ check out [pymush](https://github.com/volundmush/pymush)

  __Q:__ Why not just feed data straight to TelnetConnection? Why manually create TelnetFrames first?  
  __A:__ Eventually, I want to add MCCP3 support, which would call for decompressing incoming data. Since the client will send data to trigger the server understanding that all following data will be compressed, Frames must be parsed one at a time so that any remaining data can be optionally decompressed. It's easy to create a 'BufferedTelnetConnection' subclass that handles all of this for you, though.

## Special Thanks
  * The Evennia Project. A bit of code's yoinked from them, and the dual-process idea for Portal+Server is definitely from them.
  * All of my Patrons on Patreon.
  * Anyone who contributes to this project or my other ones.