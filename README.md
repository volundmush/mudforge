# MudForge - A Barebones MU* Framework for Python

## WARNING: Early Alpha!
Pardon our dust, this project is still in its infancy. It runs, but if you're not a developer intent on sprucing up, it may not have much for you just yet.

## CONTACT INFO
**Name:** Volund

**Email:** volundmush@gmail.com

**PayPal:** volundmush@gmail.com

**Discord:** Volund#1206  

**Discord Channel:** https://discord.gg/Sxuz3QNU8U

**Patreon:** https://www.patreon.com/volund

**Home Repository:** https://github.com/volundmush/mudforge

## TERMS AND CONDITIONS

MIT license. In short: go nuts, but give credit where credit is due.

Please see the included LICENSE.txt for the legalese.

## INTRO
MUDs and their brethren are the precursors to our modern MMORPGs, and are still a blast to play - in addition to their other uses, such as educative game design: all the game logic, none of the graphics!

Writing one from scratch isn't easy though, so this library aims to take away a great deal of the boilerplate pain.

MudForge provides a dual-process Application framework and a launcher, where each and every piece of the program is meant to be inherited and overloaded by another developer's efforts. The MudGate process holds onto clients and communicates with the MudForge process over local private networking, allowing the game to reboot - and apply updates - without disconnecting clients.

This library isn't a MUD. It's not a MUSH, or a MUX, or a MOO, or MUCK on its own, though. In truth, it doesn't DO very much. That's a good thing! See, it doesn't make (many) decisions for the developers it's meant for, making it easy to build virtually ANY kind of text-based multiplayer game atop of it.

## FEATURES
  * Extensive Telnet Support
  * Extendable Protocol Framework
  * Amazing ANSI and other Text Formatting powered by [Rich](https://github.com/willmcgugan/rich)

## UNFINISHED FEATURES
  * TLS Support
  * WebSocket Support
  * SSH Support
  * Integrated WebClient


## OKAY, BUT HOW DO I USE IT?
Glad you asked!

You can install MudForge using ```pip install git+git://github.com/volundmush/mudforge```

This adds the `mudforge` command to your shell. use `mudforge --help` to see what it can do.

The way that athanor and projects built on it work:

`mudforge --init <folder>` will create a folder that contains your game's configuration, save files, database, and possibly some code. Enter the folder and use `mudforge start` and `mudforge stop` to control it. you can use `--app mudgate` or `--app mudforge` to start/stop specific programs.

Examine the profile folder's .yaml files to learn how to change the server's configuration around.

Again, though, it doesn't do much...

## OKAAAAAAY, SO HOW DO I -REALLY- USE IT?
The true power of MudForge is in its extendability. Because you can replace any and all classes the program uses for its startup routines, and the launcher itself is a class, it's easy-peasy to create a whole new library with its own command-based launcher and game template that the launcher creates a skeleton of with `--init <folder>`.

Not gonna lie though - that does need some Python skills.


## FAQ 
  __Q:__ This is cool! How can I help?  
  __A:__ [Patreon](https://www.patreon.com/volund) support is always welcome. If you can code and have cool ideas or bug fixes, feel free to fork, edit, and pull request! Join our [discord](https://discord.gg/Sxuz3QNU8U) to really get cranking away though.

  __Q:__ I found a bug! What do I do?  
  __A:__ Post it on this GitHub's Issues tracker. I'll see what I can do when I have time. ... or you can try to fix it yourself and submit a Pull Request. That's cool too.

## Special Thanks
  * The Evennia Project. A bit of code's yoinked from them, and the dual-process idea for Portal+Server is definitely from them.
  * All of my Patrons on Patreon.
  * Anyone who contributes to this project or my other ones.
