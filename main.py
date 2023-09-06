import tkinter as tk
from numpy.random import binomial, normal, choice
import math
from colour import Color
from time import sleep
from threading import Thread
import sys

# ------GLOBAL VARS--------------------------------------------------------------
##--------parameters------------------------------------------------------------
worldwidth = 750
worldheight = 660
rownr = 50
colnr = 50
hexagonsize = 8
waterpercent = 25
fertilityhotspots = 20
sailreach = 5  # how far can an army sail
lefttopcornerhexagon = [20, 50]
year = 0  # start year
rounds = 5000
growth_rate = 0.02  # population growth
soldierpercent = 0.1
citynamesfile = "citynames.txt"
MAX_POPULATION = 10000000

##-----------dont change--------------------------------------------------------
colors = [
    "#" + "".join([choice(list("0123456789ABCDEF")) for j in range(6)])
    for i in range(200)
]
colorsinuse = ["#0000FF"]  # blue
mygons = [
    [None for j in range(colnr)] for i in range(rownr)
]  # the actual hexagons on the canvas
citysigns = [[None for j in range(colnr)] for i in range(rownr)]
capitalsigns = [[None for j in range(colnr)] for i in range(rownr)]
land = [[True for j in range(colnr)] for i in range(rownr)]  # land vs water bool
tiles = [[None for j in range(colnr)] for i in range(rownr)]  # the tile objects
empires = []
landtiles = []
coasttiles = []
watertiles = []
yearcounter = None
hexagonwidth = math.sqrt(3) * hexagonsize
hexagon_centres_ydiff = 2 * 3 / 4 * hexagonsize
f = open(citynamesfile, "r")
citynames = [name[:-1] for name in f]
f.close()
MAX_DISTANCE = math.sqrt(worldwidth**2 + worldheight**2)

# --------------------Stats------------------------------------------------------
worldpop = 0
biggestcity = None
biggestcitypop = 0

# ------------------------------SOME FUNCTIONS-----------------------------------


def truncnorm(mean, sd, a, b):
    return min(max(a, normal(mean, sd)), b)


# give the i'th corner of a hexagon with given center and size
def hexcorner(center, size, i):
    angle_deg = 60 * i - 30
    angle_rad = math.pi / 180 * angle_deg
    return [
        center[0] + size * math.cos(angle_rad),
        center[1] + size * math.sin(angle_rad),
    ]


def findneighbors(i, j):
    neighbors = []
    if i > 0:
        neighbors.append([i - 1, j])
        if i % 2 == 0 and j < colnr - 1:
            neighbors.append([i - 1, j + 1])
        elif i % 2 == 1 and j > 0:
            neighbors.append([i - 1, j - 1])
    if i < rownr - 1:
        neighbors.append([i + 1, j])
        if i % 2 == 0 and j < colnr - 1:
            neighbors.append([i + 1, j + 1])
        elif i % 2 == 1 and j > 0:
            neighbors.append([i + 1, j - 1])
    if j > 0:
        neighbors.append([i, j - 1])
    if j < colnr - 1:
        neighbors.append([i, j + 1])
    return neighbors


def distance(coord1, coord2):
    x = abs(coord1[0] - coord2[0])
    y = abs(coord1[1] - coord2[1])
    return math.sqrt(x**2 + y**2)


# ------------------------------Tile class---------------------------------------
class Tile:
    def __init__(self, i, j):
        self.i = i
        self.j = j
        aux = 0
        if i % 2 != 0:
            aux = -0.5 * hexagonwidth
        self.x = lefttopcornerhexagon[0] + j * hexagonwidth + aux
        self.y = lefttopcornerhexagon[1] + i * hexagon_centres_ydiff
        self.neighbors = []
        self.waterneighbors = []
        self.landneighbors = []
        self.land = land[i][j]
        self.color = "blue"
        self.fertilitycolor = "blue"
        self.disttosea = -1
        if self.land:
            self.coast = False
            self.sailables = set()
            self.color = "white"
            self.fertilitycolor = "white"
            self.fertilityspot = False
            self.disttofertilityspot = -1
            self.fertility = 0
            self.treasure = 41
            self.food = 0
            self.population = max(100, round(normal(100, 200)))
            self.soldiers = round(self.population * soldierpercent)
            self.citystatus = 0
            self.empire = None  # empire to which tile belongs
            self.unrest = 0
            self.rebelyear = 0

    def foundcity(self, canvas, historylog):
        self.citystatus = 1
        self.name = "dummyname"
        if len(citynames) > 0:
            self.name = choice(citynames)
            citynames.remove(self.name)
        citysigns[self.i][self.j] = canvas.create_oval(
            self.x - 4,
            self.y - 4,
            self.x + 4,
            self.y + 4,
            fill="black",
            tags=("cit" + str(self.i), "cit" + str(self.j)),
        )
        if self.empire == None:
            self.foundempire(canvas, historylog, True)
        else:
            self.empire.empirecities.add(self)

    def foundempire(self, canvas, historylog, report):
        self.citystatus = 2
        capitalsigns[self.i][self.j] = canvas.create_oval(
            self.x - 3,
            self.y - 3,
            self.x + 3,
            self.y + 3,
            fill="gold",
            tags=("cap" + str(self.i), "cap" + str(self.j)),
        )
        self.color = choice(colors)
        while self.color in colorsinuse:
            self.color = choice(colors)
        colorsinuse.append(self.color)
        self.empire = Empire(self)
        if report:
            historylog.insert(
                tk.END, str(year) + ": " + self.empire.name + " founded\n"
            )
            historylog.see(tk.END)
        empires.append(self.empire)
        canvas.itemconfig(mygons[self.i][self.j], fill=self.color)

    def conquered(self, victor, canvas, historylog):
        if self.citystatus == 2:
            self.empire.destroyed(victor, canvas, historylog)
        else:
            if self.empire != None:
                self.empire.empiretiles.remove(self)
                if self.citystatus == 1:
                    self.empire.empirecities.remove(self)
                self.empire.updateborders()
            self.empire = victor
            victor.empiretiles.add(self)
            if self.citystatus == 1:
                victor.empirecities.add(self)
            victor.updateborders()
            self.color = victor.color
            canvas.itemconfig(mygons[self.i][self.j], fill=self.color)

    def switchempire(self, oldempire, newempire, canvas):
        self.empire = newempire
        oldempire.empiretiles.remove(self)
        newempire.empiretiles.add(self)
        if self.citystatus == 1:
            oldempire.empirecities.remove(self)
            newempire.empirecities.add(self)
        self.color = newempire.color
        canvas.itemconfig(mygons[self.i][self.j], fill=self.color)

    def rebel(self, canvas, historylog, switchrate):
        rulers = self.empire
        if self.citystatus == 0:
            self.foundcity(canvas, historylog)
        rulers.empirecities.remove(self)
        self.foundempire(canvas, historylog, False)
        historylog.insert(
            tk.END,
            str(year)
            + ": Rebellion! by "
            + self.name
            + " against the "
            + rulers.name
            + "\n",
            "rebel",
        )
        historylog.see(tk.END)
        self.unrest = 0
        for n in rulers.empiretiles:
            if (
                n.empire == rulers
                and n.citystatus < 2
                and n.closestempirecity(rulers) == self
            ):
                n.switchempire(rulers, self.empire, canvas)
                n.unrest = 0
        rulers.empiretiles.remove(self)
        rulers.updateborders()
        self.empire.updateborders()
        switchers = round(switchrate * rulers.armysize)
        self.empire.armysize += switchers
        rulers.armysize -= switchers

    def closestempirecity(self, empire):
        closest = empire.capital
        bestdist = distance([self.x, self.y], [empire.capital.x, empire.capital.y])
        for city in empire.empirecities:
            dist = distance([self.x, self.y], [city.x, city.y])
            if dist < bestdist:
                bestdist = dist
                closest = city
        return [bestdist, closest]

    # How valuable is this tile potentially for a given empire
    def potentialvalue(self, empire):
        dist = self.closestempirecity(empire)[0]
        disttocapital = distance([self.x, self.y], [empire.capital.x, empire.capital.y])
        return (
            self.fertility + self.treasure - dist - disttocapital + 50 * self.citystatus
        )


# ------------------Impire Class-------------------------------------------------
class Empire:
    def __init__(self, city):
        self.capital = city
        self.color = city.color
        self.empiretiles = {city}
        self.bordertiles = {city}
        self.empirecities = {city}
        self.borderlines = 6
        self.armysize = city.soldiers
        self.name = "Empire of " + city.name
        self.streak = 0
        self.age = 0

    def destroyed(self, victor, canvas, historylog):
        historylog.insert(
            tk.END,
            str(year) + ": " + self.name + " destroyed by " + victor.name + "\n",
            "destroyed",
        )
        historylog.see(tk.END)
        self.capital.citystatus = 1
        canvas.delete(capitalsigns[self.capital.i][self.capital.j])
        self.capital.conquered(victor, canvas, historylog)
        for city in self.empirecities:
            city.foundempire(canvas, historylog, True)
        auxlist = [tile for tile in self.empiretiles]
        for tile in auxlist:
            if tile.citystatus == 0:
                closestcity = tile.closestempirecity(self)[1]
                tile.conquered(closestcity.empire, canvas, historylog)
        empires.remove(self)

    def updateborders(self):
        self.bordertiles = set()
        self.borderlines = 0
        for tile in self.empiretiles:
            border = False
            for n in tile.landneighbors + list(tile.sailables):
                if n.empire != self:
                    border = True
                    self.borderlines += 1
            if border:
                self.bordertiles.add(tile)

    def recruit(self, tile):
        recruited = math.floor(tile.soldiers * 0.5)
        tile.soldiers -= recruited
        return recruited

    def updatearmy(self):
        self.armysize = round(self.armysize * 0.96)  # retirement
        for tile in self.empiretiles:
            self.armysize += self.recruit(tile)

    def findexpantions(self):
        mostpromising = None
        relevantborder = None
        record = -float("Inf")
        for tile in self.bordertiles:
            for n in tile.landneighbors + list(tile.sailables):
                if n.empire != self:
                    potential = n.potentialvalue(self)
                    if n.soldiers <= self.armysize:
                        potential += 50
                    if n.empire == None:
                        potential += 100
                    if potential > record:
                        record = potential
                        mostpromising = n
                        relevantborder = tile
        return relevantborder, mostpromising, record

    def distribute(self):
        food = sum(tile.food for tile in self.empiretiles)
        importanttiles = sorted(
            self.empiretiles, key=lambda x: x.potentialvalue(self), reverse=True
        )
        totalpop = sum(tile.population for tile in self.empiretiles)
        i = 0
        while food > 0 and i < len(self.empiretiles):
            tile = importanttiles[i]
            given = max(MAX_POPULATION / 1000, min(food, round(tile.population / 1000)))
            tile.food += given
            food -= given
            i += 1
        i = 0
        j = 10
        while food > 0:
            extragiven = math.ceil(j / 100 * food)
            if importanttiles[i].population < MAX_POPULATION:
                importanttiles[i].food += extragiven
                food -= extragiven
            i += 1
            j -= 1 * int(j > 2)
            if i == len(self.empiretiles):
                i = 0

            # if i == len(self.empiretiles) - 1 or importanttiles[i].population < 2*importanttiles[i+1].population:
            #   extragiven = math.ceil(food/2)
            #   importanttiles[i].food += extragiven
            #   food -= extragiven
            #   i += 1
            #   if i == len(self.empiretiles):
            #     i = 0
            # while importanttiles[j].population > MAX_POPULATION:
            #    j += 1
            # extragiven = max(1, round(food/(2**(i+1))))
            # importanttiles[j].food += extragiven
            # food -= extragiven
            # i += 1
            # j += 1
            # if j == len(self.empiretiles):
            #    i = 0
            #    j = 0


# -----------------------MakeWorld-----------------------------------------------
def drawcanvas(canvas):
    for i in range(rownr):
        for j in range(colnr):
            tile = tiles[i][j]
            canvas.itemconfig(mygons[i][j], fill=tiles[i][j].fertilitycolor)


# also calculates the distance tot the sea
def setfertility():
    global tiles
    hotspots = choice(landtiles, fertilityhotspots, replace=False)
    for tile in hotspots:
        tile.fertilityspot = True
        tile.disttofertilityspot = 0
    for tile in coasttiles:
        tile.disttosea = 0
        tile.fertilityspot = True
        tile.disttofertilityspot = 0
    dist = 1
    done = False
    while not done:
        done = True
        for tile in landtiles:
            if tile.disttosea == -1:
                done = False
                for n in tile.neighbors:
                    if n.disttosea == dist - 1:
                        tile.disttosea = dist
                        break
            if tile.disttofertilityspot == -1:
                done = False
                for n in tile.neighbors:
                    if n.disttofertilityspot == dist - 1:
                        tile.disttofertilityspot = dist
                        break
        dist += 1
    greenrange = list(Color("white").range_to(Color("green"), 101))
    greenrange = greenrange[25:]
    for tile in landtiles + coasttiles:
        tile.fertility = min(75, max(0, normal(60 - 7 * tile.disttofertilityspot, 5)))
        tile.fertilitycolor = greenrange[round(tile.fertility)]


# RECURSIE :D
def sailableneighbors(sailables, fromtile, mytile, depth):
    if depth == sailreach:
        return sailables
    if not mytile.land:
        for n in mytile.landneighbors:
            if not n == fromtile:
                sailables.add(n)
    for n in mytile.waterneighbors:
        sailables = sailableneighbors(sailables, fromtile, n, depth + 1)
    return sailables


def setsailables():
    global coasttiles
    for tile in coasttiles:
        tile.sailables = sailableneighbors(tile.sailables, tile, tile, 0)


# bit of bookkeeping, setting neighbors and such
def initialize():
    global tiles, landtiles, coasttiles, watertiles
    for i in range(rownr):
        for j in range(colnr):
            tile = tiles[i][j]
            neighbors = findneighbors(i, j)
            for n in neighbors:
                ntile = tiles[n[0]][n[1]]
                tile.neighbors.append(ntile)
                if ntile.land:
                    tile.landneighbors.append(ntile)
                else:
                    tile.waterneighbors.append(ntile)
            if not tile.land:
                watertiles.append(tile)
            elif len(tile.waterneighbors) > 0 or len(tile.neighbors) < 6:
                coasttiles.append(tile)
                tile.coast = True
            else:
                landtiles.append(tile)


def resetcanvas(canvas):
    global land, tiles, coasttiles, watertiles, landtiles, year, citysigns, empires, capitalsigns
    canvas.delete(yearcounter)
    for i in range(rownr):
        for j in range(colnr):
            canvas.delete(mygons[i][j])
            if citysigns[i][j] != None:
                canvas.delete(citysigns[i][j])
            if capitalsigns[i][j] != None:
                canvas.delete(capitalsigns[i][j])
    land = [[True for j in range(colnr)] for i in range(rownr)]  # reset canvas
    tiles = [[None for j in range(colnr)] for i in range(rownr)]
    citysigns = [[None for j in range(colnr)] for i in range(rownr)]
    capitalsigns = [[None for j in range(colnr)] for i in range(rownr)]
    landtiles = []
    coasttiles = []
    watertiles = []
    empires = []
    year = 0
    canvas.update_idletasks()


def determinewater():
    global land
    water = 0
    watergoal = waterpercent / 100 * rownr * colnr
    while water < watergoal:
        for i in range(rownr):
            for j in range(colnr):
                prop = 0.0005
                neighbors = findneighbors(i, j)
                prop += (6 - len(neighbors)) * 0.08
                for neighbor in neighbors:
                    if not land[neighbor[0]][neighbor[1]]:
                        prop += 0.3
                prop = min(1, prop)
                if binomial(1, prop) == 1:
                    water += 1
                    land[i][j] = False


def makehexagons(canvas):
    for i in range(rownr):
        for j in range(colnr):
            mycol = "white"
            myoutline = "black"
            if not land[i][j]:
                mycol = "blue"
                myoutline = "blue"
            aux = 0
            if i % 2 != 0:
                aux = -0.5 * hexagonwidth
            center = [
                lefttopcornerhexagon[0] + j * hexagonwidth + aux,
                lefttopcornerhexagon[1] + i * hexagon_centres_ydiff,
            ]
            corners = [hexcorner(center, hexagonsize, k) for k in range(6)]
            mygons[i][j] = canvas.create_polygon(
                corners[0][0],
                corners[0][1],
                corners[1][0],
                corners[1][1],
                corners[2][0],
                corners[2][1],
                corners[3][0],
                corners[3][1],
                corners[4][0],
                corners[4][1],
                corners[5][0],
                corners[5][1],
                fill=mycol,
                outline=myoutline,
                tags=("gon" + str(i), "gon" + str(j)),
            )


def makecontinent(canvas):
    global tiles, yearcounter, worldpop
    resetcanvas(canvas)
    determinewater()
    makehexagons(canvas)
    yearcounter = canvas.create_text(
        10, 10, text="Year: 0", anchor="nw", fill="white", font=("Purisa", 16, "bold")
    )
    tiles = [[Tile(i, j) for j in range(colnr)] for i in range(rownr)]
    initialize()
    setsailables()
    setfertility()
    worldpop = sum(tile.population for tile in landtiles + coasttiles)
    drawcanvas(canvas)
    canvas.update_idletasks()


# --------------------Simulation-------------------------------------------------
def harvest():
    for tile in landtiles + coasttiles:
        tile.food = round(max(0, normal(tile.fertility, 2)))


def populationchange(canvas, historylog):
    global worldpop, biggestcity, biggestcitypop
    worldpop = 0
    for tile in landtiles + coasttiles:
        surplus = tile.food * 1000 - tile.population
        expectedgrowth = min(
            surplus, round(tile.population * (growth_rate + 0.01 * tile.citystatus))
        )
        growth = round(
            truncnorm(expectedgrowth, 100, -tile.population + 100, float("Inf"))
        )
        tile.population += growth
        tile.soldiers += max(0, round(growth * soldierpercent))
        if growth < -500:
            tile.unrest += 1
        elif growth > 500:
            tile.unrest -= 1 * int(tile.unrest > 0)
        if (
            tile.citystatus == 0
            and tile.population > 60000
            and tile.treasure > 40
            and binomial(1, 0.001) == 1
        ):
            tile.foundcity(canvas, historylog)
        worldpop += tile.population
        if tile.citystatus > 0 and tile.population > biggestcitypop:
            biggestcitypop = tile.population
            biggestcity = tile


def guess(truevalue, sd):
    return round(truncnorm(truevalue, sd, 0, float("Inf")))


def battle(agressor, armybrought, defendingtile, willreinforce):
    if willreinforce:
        defendingempire = defendingtile.empire
        if armybrought >= defendingtile.soldiers:
            strengthening = min(
                defendingempire.armysize, armybrought - defendingtile.soldiers
            )
            defendingempire.armysize -= strengthening
            defendingtile.soldiers += strengthening
    morale = max(-0.2, min(0.2, normal(0, 0.01) + 0.01 * agressor.streak))
    defensebonus = defendingtile.citystatus * 0.1 + 0.4 * int(
        year - defendingtile.rebelyear < 10
    )
    avg = (
        1 + morale - defensebonus
    )  # average number of defending soldiers that 1 attacker kills
    neededforvictory = defendingtile.soldiers / avg
    if armybrought >= neededforvictory:
        agressor.armysize -= round(neededforvictory)
        agressor.streak = max(1, agressor.streak + 1)
        defendingtile.soldiers = 0
        return True
    agressor.armysize -= armybrought
    agressor.streak = min(-1, agressor.streak - 1)
    defendingtile.soldiers -= math.floor(avg * agressor.armysize)
    return False


def expand(empire, canvas, historylog):
    expgoal = empire.findexpantions()[1]
    expectreinforcements = False
    willreinforce = False
    if expgoal != None:
        expected = guess(expgoal.soldiers, 200)
        if expgoal.empire != None:
            defendingempire = expgoal.empire
            if (
                expgoal.potentialvalue(defendingempire) + 100
                > defendingempire.findexpantions()[2]
                or expgoal.citystatus == 2
            ):
                willreinforce = True
                expectreinforcements = bool(binomial(1, 0.8))
                x = guess(expgoal.empire.armysize, 200)
        troopssend = 0
        if empire.armysize > expected and not expectreinforcements:
            troopssend = min(expected + 1000, empire.armysize)

        elif expectreinforcements and empire.armysize >= x:
            troopssend = min(x + 10000, empire.armysize)
        if troopssend > 0:
            if battle(empire, troopssend, expgoal, willreinforce):
                expgoal.conquered(empire, canvas, historylog)
                canvas.update_idletasks()


def updatestats(stats):
    mytext = "Stats:\n" + "Worldpopulation: " + format(worldpop, ",") + "\n"
    if biggestcity != None:
        mytext += (
            "Bigest city : "
            + biggestcity.name
            + " with population : "
            + format(biggestcity.population, ",")
            + "\n"
        )
    if len(empires) > 0:
        biggestempire = sorted(empires, key=lambda x: len(x.empiretiles), reverse=True)[
            0
        ]
        mytext += "Bigest empire : " + biggestempire.name + "\n"
    stats.configure(text=mytext)
    stats.update_idletasks()


def rebellions(canvas, historylog):
    for empire in empires:
        capital = empire.capital
        for city in empire.empirecities:
            if city != capital:
                normdisttocapital = (
                    distance([city.x, city.y], [capital.x, capital.y]) / MAX_DISTANCE
                )
                rebelprob = (
                    city.unrest / (15 * 3)
                    + empire.age / (1500 * 3)
                    + normdisttocapital / 3
                    + 0.1 * int(empire.armysize < 10000)
                )
                rebelprob = min(rebelprob, 1)
                if binomial(1, rebelprob / 50):
                    expectedswitchrate = (
                        0.1
                        + empire.age / 1500
                        + 0.1 * abs(empire.streak) * int(empire.streak < 0)
                    )
                    expectedswitchrate = min(1, expectedswitchrate)
                    switchrate = truncnorm(expectedswitchrate, 0.3, 0, 1)
                    if switchrate > 0.5:
                        city.rebel(canvas, historylog, switchrate)
                        city.rebelyear = year
                        break


def simulate(canvas, historylog, stats):
    global tiles, year
    for year in range(rounds):
        for empire in empires:
            empire.age += 1
        rebellions(canvas, historylog)
        updatestats(stats)
        harvest()
        for empire in empires:
            empire.distribute()
        populationchange(canvas, historylog)
        for empire in empires:
            empire.updatearmy()
        for empire in empires:
            expand(empire, canvas, historylog)
        if len(empires) > 0:
            sleep(0.1)
        canvas.itemconfig(yearcounter, text="Year: " + str(year))
        canvas.update_idletasks()
        historylog.update_idletasks()


# ---------------------The App---------------------------------------------------
class application:
    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(self.parent)
        self.frame.grid(row=0)
        self.quitbutton = tk.Button(self.frame, text="Quit", command=lambda: sys.exit())
        self.quitbutton.grid(row=0, column=0, sticky=tk.W + tk.E)
        self.canvas = tk.Canvas(
            self.frame, width=worldwidth, height=worldheight, bg="blue"
        )
        self.canvas.bind("<ButtonPress-1>", self.hoverovercanvas)
        self.canvas.grid(row=1, columnspan=3, rowspan=2)
        self.tag = self.canvas.create_text(300, 10, text=" ", anchor="nw")
        self.historylog = tk.Text(self.frame, width=60, height=2)
        self.historylog.grid(row=1, column=3, sticky=tk.N + tk.S)
        self.s = tk.Scrollbar(self.frame)
        self.s.grid(row=1, column=4, sticky=tk.N + tk.S)
        self.s.config(command=self.historylog.yview)
        self.historylog.config(yscrollcommand=self.s.set)
        self.historylog.tag_configure("destroyed", foreground="red")
        self.historylog.tag_configure("rebel", foreground="purple")
        self.stats = tk.Label(
            self.frame, text="Stats:", anchor="nw", justify=tk.LEFT, bg="lightblue"
        )
        self.stats.grid(row=2, column=3, sticky=tk.N + tk.S + tk.W + tk.E)
        self.makebutton = tk.Button(
            self.frame,
            text="Make a random continnent",
            command=lambda: makecontinent(self.canvas),
        )
        self.makebutton.grid(row=0, column=1, sticky=tk.W + tk.E)
        self.startbutton = tk.Button(
            self.frame,
            text="Start simulation",
            command=lambda: Thread(
                target=simulate, args=(self.canvas, self.historylog, self.stats)
            ).start(),
        )
        self.startbutton.grid(row=0, column=2, sticky=tk.W + tk.E)

    def hoverovercanvas(self, event):
        cnv = self.canvas
        item = cnv.find_closest(cnv.canvasx(event.x), cnv.canvasy(event.y))[0]
        tags = cnv.gettags(item)
        message = " "
        if len(tags) > 1:
            i = int(tags[0][3:])
            j = int(tags[1][3:])
            tile = tiles[i][j]
            if land[i][j] and tile.citystatus > 0:
                message = (
                    tile.name + ", Population: " + format(tile.population, ",") + ", "
                )
            if land[i][j] and tile.empire != None:
                message += (
                    tile.empire.name
                    + ", Armysize: "
                    + format(tile.empire.armysize, ",")
                )
            elif land[i][j]:
                message += " Soldiers: " + str(tile.soldiers)
            self.canvas.itemconfigure(self.tag, text=message)


# -------------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("History Generator")
    app = application(root)
    root.mainloop()
