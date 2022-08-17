# termuxtracker
minimal Android GPS tracker using termux-location running on termux python3

this project is for study only. If you need a mature solution, check out [traccar](https://github.com/traccar/traccar)

# How does it work? 
client periodically acquires location by calling termux-location, and reports location to server by UDP packets. That's it! 
