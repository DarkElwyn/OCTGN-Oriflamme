# -- coding: utf-8 --
import re
from datetime import datetime
import time

pendingInfluenceMarker = ("Influence en attente", "00000001-0000-0092-0001-100000000000")
currentInfluenceMarker = ("Influence actuelle", "00000001-0000-0092-0001-100000000001")

highlightColor = "#ffffff"

######################
####### EVENTS #######
######################

def OnCounterChanged(args):
	if args.counter.value < 0 :
		args.counter.value = 0
	refreshCounters()

def OnCardsMoved(args):
	index = -1
	if args.player == me:
		for card in args.cards:
			index += 1
			#whisper(str(card.position))
			# les cartes bloquées ne bougent pas
			if args.fromGroups[0] == table and args.toGroups[0] == table:
				if "Blocked" in card.type:
					oldZIndex = card.index
					card.moveToTable(args.xs[index], args.ys[index], True)
					card.index = oldZIndex

def OnCardDoubleClicked(args):
	card = args.card
	if "Played" in card.type:
		if card.owner == me and "Revealed" not in card.type:
			reveal(card)
		else:
			eliminate(card)
	if "Player" in card.type:
		steal(card)

def OnTurnPassed(args):
	if iAmHost():
		if turnNumber() == 6:
			notify("C'est le dernier tour !")
		if turnNumber() == 7:
			winner = calculateWinner()
			printGameDuration()
			notifyBarAll("La partie est terminée, {} est victorieux avec {} points d'influence et {} cartes dans la File !".format(winner, winner.influence, winner.cardsCount-1), "#000000")
		
		setFirstTokenPositionToNext()

def OnPhasePassed(args):
	if iAmHost():
		nextRank = eval(getGlobalVariable("rankCurrentHighlight")) + 1
		setGlobalVariable("rankCurrentHighlight",str(nextRank))
		refreshHighlight()

######################
####### SETUP  #######
######################	

def setup():
	if iAmHost():
		notify("Regles du jeu : https://darkelwyn.github.io/octgn/Oriflamme/")
		setGlobalVariable("dateTimeDebut", time.mktime(datetime.now().timetuple()))
		whisper("Je suis l'hôte")
		colors = [0, 100, 200, 300, 400]
		colors.sort(key=lambda x:rnd(0, 20))
		
		index = 0
		for p in getPlayers():
			remoteCall(p, "personnalSetup", [colors[index], index])
			index += 1
		nextTurn(force=True)
		
		table.create("00000001-0000-0092-0001-000000000500",0,0).type = "Token|Blocked"
		setFirstTokenPositionToNext(rnd(0, len(getPlayers())-1))

def personnalSetup(colorModifier, playerPosition):
	createRangeCards(me.hand, 1+colorModifier, 10+colorModifier)
	for i in range(0, 2):
		me.hand.random().moveTo(me.famille)
	firstPlayerCard = me.hand.random()
	firstPlayerCard.moveToTable(getXCoordinatePlayerZone(playerPosition),0, True)
	firstPlayerCard.type = "Player|Blocked"
	firstPlayerCard.sendToBack()
	refreshCounters()

######################
####### UTILS  #######
######################

def iAmHost():
	return me._id == 1

def isAssassinat(card):
	return card.model.endswith("2")

def isEmbuscade(card):
	return card.model.endswith("6")

def isComplot(card):
	return card.model.endswith("4")

def isDiscardable(card):
	return card.model.endswith(("2","4","5","6"))

def canInc(card, x = 0, y = 0):
	return "Played" in card[0].type and card[0].isFaceUp == False and card[0].owner == me

def canBeStupid(card,b=0,c=0):
	return ("Played" in card[0].type or "Garbage" in card[0].type) and card[0].isFaceUp == True and card[0].owner == me

def getOneCardOnTableByType(type = ""):
	for card in table:
		if type in card.type:
			return card

def remoteCallAll(functionName, params = []):
	mute()
	for p in getPlayers():
		remoteCall(p,functionName,params)

def notifyBarAll(message, color = "#FF0000"):
	message += " " * 500
	remoteCallAll("notifyBar",[color,message])
	notify(message)

def createRangeCards(destination, fromID, toID):
	for i in range(fromID, toID+1):
		destination.create("00000001-0000-0092-0001-000000000{}".format(str(i).zfill(3)))

def printGameDuration(a=0,b=0,c=0):
	begin = datetime.fromtimestamp(eval(getGlobalVariable("dateTimeDebut")))
	duration = datetime.utcfromtimestamp((datetime.now() - begin).total_seconds())
	notify("La partie a durée {}".format(duration.strftime('%Hh%Mmin')))

def calculateWinner():
	winner = me
	winner.cardsCount = cardsOnTheBoard(me)
	for player in getPlayers():
		player.cardsCount = cardsOnTheBoard(player)
		if player.influence > winner.influence:
			winner = player
		elif player.influence == winner.influence:
			if player.cardsCount > winner.cardsCount:
				winner = player
	return winner

def cardsOnTheBoard(player):
	return 10 - len(player.hand) - len(player.famille) - len(player.défausse)

def getXCoordinatePlayerZone(playerIndex):
	totalPlayers = len(getPlayers())
	totalWidth = totalPlayers * 130
	start = 12 - totalWidth/2
	return start + playerIndex * 130

def setFirstTokenPositionToNext(inc = 1):
	oldRank = eval(getGlobalVariable("rankFirstPlayer"))
	newRank = (oldRank + inc) % len(getPlayers())
	
	token = getOneCardOnTableByType("Token")
	token.moveToTable(getXCoordinatePlayerZone(newRank)+10,-30)
	token.sendToFront()
	
	newFirstPlayer = getPlayers()[newRank]
	setGlobalVariable("rankFirstPlayer",str(newRank))
	notify("Le premier joueur est {}".format(newFirstPlayer))
	refreshHighlight()

def refreshHighlight():
	currentPosition = eval(getGlobalVariable("rankCurrentHighlight"))
	
	if currentPosition < len(getPlayers()): # d'abord les zones joueurs
		firstPlayerRank = eval(getGlobalVariable("rankFirstPlayer"))
		
		highlightedPlayerIndex = (firstPlayerRank + currentPosition) % len(getPlayers())
		highlightedPlayer = getPlayers()[highlightedPlayerIndex]
		
		for card in table:
			if "Player" in card.type:
				if card.owner == highlightedPlayer:
					card.highlight = highlightColor
				else:
					card.highlight = None
	
	else:
		# d'abord on enlève l'highlight de toutes les autres cartes
		for card in table:
			if "Player" in card.type:
					card.highlight = None
		
		# ensuite on s'occupe des cartes jouées
		highlightedCards = [card for card in table if card.highlight == highlightColor]
		if len(highlightedCards) > 0:
			currentX = highlightedCards[0].position[0]
		else:
			currentX = -9999
						
		playedCards = [card for card in table if "Played" in card.type or "Garbage" in card.type]
		playedCards.sort(key=lambda x:x.position[0]) # sort by X coordinaate
		
		found = False
		for card in playedCards:
			if card.position[0] > currentX and not found:
				card.highlight = highlightColor
				found = True
			else:
				card.highlight = None
		
		if not found:
			turnInc()

def turnInc():
	arrange()
	setGlobalVariable("rankCurrentHighlight",str(0))
	if turnNumber() <= 6:
		nextTurn(force=True)

def searchForOutterCardX(type = ""):
	cardWidth = 95
	xMax = -6 - cardWidth*1.5
	xMin = -6 + cardWidth*0.5
	for card in table:
		if type in card.type:
			x, y = card.position
			if x > xMax:
				xMax = x
			if x < xMin:
				xMin = x
	
	return (xMin - cardWidth, xMax + cardWidth)

def markAsGarbage(card):
	mute()
	card.type = "Garbage"
	x, y = card.position
	card.moveToTable(x, y+50)

def refreshCounters():
	for card in table:
		if "Player" in card.type:
			card.markers[currentInfluenceMarker] = card.owner.influence

######################
#### PILE ACTIONS ####
######################

def shuffle(group, x = 0, y = 0):
    mute()
    group.shuffle()
    notify("{} mélange sa {}.".format(me, group.name))

######################
#### HAND ACTIONS ####
######################

def playCardR(card, x = 0, y = 0):
	mute()
	leftX, rightX = searchForOutterCardX("Played")
	card.moveToTable(rightX, -255, True)
	card.type = "Played"
	notify("{} joue une carte à droite de la File".format(me))
	setHighlightToNext()

def playCardL(card, x = 0, y = 0):
	mute()
	leftX, rightX = searchForOutterCardX("Played")
	card.moveToTable(leftX, -255, True)
	card.type = "Played"
	notify("{} joue une carte à gauche de la File".format(me))
	setHighlightToNext()

#######################
#### TABLE ACTIONS ####
#######################

def reveal(card):
	card.isFaceUp = True
	card.type = "Played|Revealed"
	mute()
	
	points = card.markers[pendingInfluenceMarker]
	card.markers[pendingInfluenceMarker] = 0
	
	if isEmbuscade(card):
		points = 1
	if isComplot(card):
		points *= 2
	if isDiscardable(card):
		markAsGarbage(card)

	me.influence += points
	notify("{} révèle un {} et marque {} points d'influence".format(me, card.Name, points))

def eliminate(card, x = 0, y = 0):
	card.isFaceUp = True
	mute()
	markAsGarbage(card)
	card.markers[pendingInfluenceMarker] = 0
	me.influence += 1
	notify("{} détruit {} de {} et marque 1 point d'influence".format(me, card, card.owner))
	
	if isEmbuscade(card):
		card.owner.influence += 4
		notify("{} marque 4 points d'influence".format(card.owner))

def arrange(group = (), x = 0, y = 0):
	# on fait le ménage
	for card in table:
		if "Garbage" in card.type:
			card.moveTo(card.owner.défausse)
	# on comble les trous
	playedCards = [card for card in table if "Played" in card.type]
	index = -6 -(len(playedCards) * 95 / 2)
	playedCards.sort(key=lambda x:x.position[0])
	for card in playedCards:
			card.moveToTable(index, -255)
			index += 95

def setHighlightToNext(a=0,b=0,c=0):
	setPhase(1)

def steal(card):
	mute()
	if card.owner.influence < 1:
		notify("{} ne peut pas voler de l'influence à {} car il n'en a pas (0 point)".format(me, card.owner))
	elif card.owner == me:
		notify("{} est schizophrène, il essaie de se voler lui même !".format(me))
	else:
		card.owner.influence -= 1
		me.influence += 1
		notify("{} vole 1 influence à {}".format(me, card.owner))

def incCardInfluence(card, x = 0, y = 0):
	card.markers[pendingInfluenceMarker] += 1

def flipBack(card, x=0, y=0):
	card.isFaceUp = False
	card.type = "Played"