# -*- coding: utf-8 -*-

#
# chess pieces font from https://github.com/xeyownt/chess_merida_unicode
# licence: free
#
# TODO:
# - Spielzeit/Uhr als Alternative zur Spielstärke
# - Remis anbieten (möglich?)
# - Info-Handler aus python-chess
# - Absichern, dass gnuchess installiert ist
# - Absichern, dass python-chess installiert ist
# - Ohne Computer spielen
# - Stellung eingeben
# - Spiel abbrechen/resetten
# - Spiel speichern, laden, fortsetzen
# - Bedienung vereinfachen:
#   ausgewählte Figur nur auf erlaubten Bahnen bewegen
#

from enigma import gFont, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Sources.CanvasSource import CanvasSource   
from Components.Sources.StaticText import StaticText   
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox

import chess
import chess.uci

class Gnuchess(object):
	
	def __init__(self, callback):
		
		self.callback = callback
	
		self.engine = chess.uci.popen_engine([ "/usr/bin/gnuchess", "-u"] )
		self.engine.uci()
		self.engine.setoption({ "BookFile": "smallbook.bin" })
		self.engine.isready()
		self.engine.ucinewgame()
		
		self.movetime = 1000
		
	def quit(self):
		try:
			self.engine.terminate()
		except Exception:
			pass
	
	def received(self, future):
		result = future.result()
		bestmove = None
		ponder = None
		if result.bestmove:
			bestmove = result.bestmove.uci()
		if result.ponder:
			ponder = result.ponder.uci()
		self.callback(bestmove, ponder)
		
	def doMove(self, board):
		self.engine.position(board)
		future = self.engine.go(movetime=self.movetime, async_callback=self.received)
	
	def setMovetime(self, movetime):
		try:
			self.movetime = int(movetime)
		except Exception:
			pass
	
	def getMovetime(self):
		return self.movetime
	

def argb(a,r,g,b):
	return (a<<24)|(r<<16)|(g<<8)|b

class ChessBoard(chess.Board):
	boardcolor = { 
		"black": argb(0x00, 0x00, 0x00, 0x00), 
		"dark":  argb(0x00, 0xd9, 0xd9, 0xc5), 
		"light": argb(0x00, 0xff, 0xff, 0xff), 
		"focus": argb(0x00, 0xcc, 0x22, 0x22)
	}
	
	cellwidth = 100
	fontsize  = 60
	
	def __init__(self, fen=chess.STARTING_FEN, chess960=False, canvas=None):
		chess.Board.__init__(self, fen=chess.STARTING_FEN, chess960=False)
		self.canvas = canvas

		self.WhiteBottom = True
		self.drawCoords()

		self._focusSquare = 12
		self._isCastling = False
		self._isEnpassant = False
		
		self.pieceColor = self.boardcolor["black"]
		self.frameColor = self.boardcolor["black"]
		
	
	def drawCoords(self):
		if self.canvas:
			self.canvas.fill(0, 0, 30, self.cellwidth*8+40, self.boardcolor["light"])
			self.canvas.fill(00, 810, self.cellwidth*8+40, 30, self.boardcolor["light"])
			for coord in range(1,9):
				if self.WhiteBottom:
					hchar = chr(96+coord)
					vchar = chr(57-coord)
				else:
					hchar = chr(105-coord)
					vchar = chr(48+coord)
				offset = (coord-1) * self.cellwidth
				self.canvas.writeText(0, offset, 30, self.cellwidth, 
					self.boardcolor["black"], self.boardcolor["light"],
					gFont("Regular", 24), vchar, 
					RT_HALIGN_CENTER|RT_VALIGN_CENTER)
				self.canvas.writeText(offset+40, 810, self.cellwidth, 30, 
					self.boardcolor["black"], self.boardcolor["light"],
					gFont("Regular", 24), hchar, 
					RT_HALIGN_CENTER|RT_VALIGN_CENTER)
	
	def rotateBoard(self):
		self.WhiteBottom = not self.WhiteBottom
		self.drawCoords()
		self.drawBoard()
	
	def push_uci(self, uci):
		"""
		Überschreibt die Library-Methode, um Rochade und en passant korrekt
		anzeigen zu können. Das Board jetzt neu zeichnen
		"""
		move = self.parse_uci(uci)
		self._isCastling = self.is_castling(move)
		self._isEnpassant = self.is_en_passant(move)
		self.push(move)
		self.updateBoard(move)
		return move

	def _getPieceAt(self, square):
		try:
			piece = self.piece_at(square).unicode_symbol()
		except:
			piece = ""
		return piece

	def drawBoard(self):
		if self.canvas:
			for square in chess.SQUARES_180:
				self._drawSquare(square)

	def updateBoard(self, move):
		# Falls der letzt Zug eine Rochade oder En-Passant war,
		# wird der Einfachheit halber das Board komplett neu
		# gezeichnet. Ansonsten nur die beiden betroffenen Felder.
		if self._isCastling or self._isEnpassant:
			self.drawBoard()
		else:
			self._drawSquare(move.from_square)
			self._drawSquare(move.to_square)
	
	def _getSquareCoord(self, square):
		x = square % 8   # x <- 0..7, => A..H
		y = square / 8   # y <- 0..7, => 1..8
		if self.WhiteBottom:
			return (x * self.cellwidth + 40, (7-y) * self.cellwidth)
		else:
			return ((7-x) * self.cellwidth + 40, y * self.cellwidth)
	
	def _getBackgroundColor(self, square):
		x = square % 8
		y = square / 8
		index = (x+y) % 2
		if index == 0:
			return self.boardcolor["dark"]
		else:
			return self.boardcolor["light"]
	
	def _getFocusColor(self, square):
		if square == self._focusSquare:
			return self.boardcolor["focus"]
		else:
			return self._getBackgroundColor(square)
	
	def _drawSquare(self, square):
		"""
		Eine Zelle zeichnen
		Für den Rahmen eine schwarze Zelle
		Darin eine etwas kleinere Zelle mit der Hintergrundfarbe und Focus
		Darin die Figur
		"""
		piece = self._getPieceAt(square)
		x, y = self._getSquareCoord(square)
		backgroundColor = self._getBackgroundColor(square)
		focusColor = self._getFocusColor(square)
		
		self.canvas.fill(x,   y,   self.cellwidth,    self.cellwidth,    self.frameColor)
		self.canvas.fill(x+1, y+1, self.cellwidth-2,  self.cellwidth-2,  focusColor)
		self.canvas.fill(x+6, y+6, self.cellwidth-12, self.cellwidth-12, backgroundColor)
		self.canvas.writeText(x+6, y+6, self.cellwidth-12, self.cellwidth-4, 
			self.pieceColor, backgroundColor, gFont("chess", self.fontsize), str(piece), 
			RT_HALIGN_CENTER|RT_VALIGN_CENTER)
		self.canvas.flush()
	
	def setFocus(self, focusSquare):
		oldFocusSquare = self._focusSquare
		self._focusSquare = focusSquare
		self._drawSquare(oldFocusSquare)
		self._drawSquare(focusSquare)
	
	def getFocus(self):
		return self._focusSquare


class Board(Screen):

	skin = """
		<screen name="ChessBoard" position="0,0" size="1920,1080" title="Chessboard" flags="wfNoBorder">
			<widget source="Canvas" render="Canvas" position="20,140" size="840,840" />
			<widget name="player_black" position="460,90" size="400,40" font="Regular;30" valign="center" halign="center" backgroundColor="#00000000" foregroundColor="#00ffffff" />
			<widget name="player_white" position="60,90" size="400,40" font="Regular;30" valign="center" halign="center" backgroundColor="#00ffffff" foregroundColor="#00000000" />
			<widget name="curr_move" position="880,100" size="350,50" font="Console;35"/>
			<widget name="hint" position="1250,100" size="650,50" font="Console;35"/>
			<widget name="message0" position="860,175" size="260,800" font="Console;30"/>
			<widget name="message1" position="1140,175" size="260,800" font="Console;30"/>
			<widget name="message2" position="1400,175" size="260,800" font="Console;30"/>
			<widget name="message3" position="1660,175" size="260,800" font="Console;30"/>
			<widget name="key_red" position="225,1015" size="280,55" zPosition="1" font="Regular; 23" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#00b81c46" />
			<widget name="key_green" position="565,1015" size="280,55" zPosition="1" font="Regular; 23" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#10389416"  />
			<widget name="key_yellow" position="905,1015" size="280,55" zPosition="1" font="Regular; 23" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#109ca81b" />
			<widget name="key_blue" position="1245,1015" size="280,55" zPosition="1" font="Regular; 23" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#008888ff" />
		</screen>
	"""

	def __init__(self, session):
		
		self.session = session
		Screen.__init__(self, session)
		self.skinName = "ChessBoard"
		
		self["actions"] =  ActionMap(["ChessboardActions"], {
			"cancel":		self.cancel,
			"up":			self.moveUp,
			"down":			self.moveDown,
			"left":			self.moveLeft,
			"right":		self.moveRight,
			"1":			self.moveUpLeft,
			"2":			self.moveUp,
			"3":			self.moveUpRight,
			"4":			self.moveLeft,
			"5":			self.selectSquare,
			"6":			self.moveRight,
			"7":			self.moveDownLeft,
			"8":			self.moveDown,
			"9":			self.moveDownRight,
			"ok":			self.selectSquare,
			"red":			self.red,
			"green":		self.green,
			"yellow":		self.yellow,
			"blue":			self.blue,
			"nextBouquet":	self.increaseMovetime,
			"prevBouquet":	self.decreaseMovetime,
		}, -1)
		
		self["Canvas"] = CanvasSource()
		
		self["curr_move"] = Label()
		self["hint"] = Label()
		
		self["message0"] = Label()
		self["message1"] = Label()
		self["message2"] = Label()
		self["message3"] = Label()
		
		self["key_red"] = Label("Zug zurücknehmen")
		self["key_green"] = Label("Zug vorschlagen")
		self["key_yellow"] = Label("Brett drehen")
		self["key_blue"] = Label("Schwarz spielen")
		
		self["player_black"] = Label("Gnuchess")
		self["player_white"] = Label("Spieler")
		
		self.gnuchess = Gnuchess(self.receiveAnswer)
		self.move  = []
		
		self.isWhite = True
		self.isGameOver = False
		self.flagUndoMove = False
		self.waitForGnuchess = False
		self.ponderMove = None
		self.whiteBottom = True
		
		self.onLayoutFinish.append(self.setupBoard)
		
	def setupBoard(self):
		self["Canvas"].fill(0,0,840,840, argb(33,255,255,255))
		self.board = ChessBoard(canvas=self["Canvas"])
		self.board.drawBoard()

	def getMoveUci(self):
		"""
		Die beiden in self.move[] gespeicherten Felder in
		UCI-Notation zurück geben
		"""
		uci = ""
		for cell in self.move:
			x = cell % 8
			y = cell / 8
			uci += chr(97+x) + chr(49+y)
		return uci

	def selectSquare(self):
		"""
		Event-Handler für OK-Taste
		Der erste Klick speichert das Feld, von dem gezogen wird
		Der zweite Klick speichert das Feld, wohin gezogen wird
		"""
		if self.isGameOver:
			return
		
		self.move.append(self.board.getFocus())
		move_uci = self.getMoveUci()
		self["curr_move"].setText(move_uci)
		if len(self.move) == 2:
			# Wenn beide Felder ausgewählt sind, wird der Zug ausgeführt.
			# Eine Bauern-Umwandlung muss gesondert behandelt werden
			if not self.handlePromotion(move_uci):
				self.playerMove(move_uci)
			self.move = []

	def playerMove(self, move_uci):
		"""
		Zug des Spielers ausführen.
		Ein illegaler Zug führt zu einer Exception, der Zug wird dann nicht
		weiter ausgeführt
		"""
		try:
			self.board.push_uci(move_uci)
			self.showMoves()
			if self.board.is_game_over(claim_draw=True):
				self["curr_move"].setText("Spielende")
				self["hint"].setText("Ausgang: "+self.board.result())
				self.isGameOver = True
				return
			elif self.board.is_check():
				self["curr_move"].setText("Schach")
			self["hint"].setText("")
			self.gnuchess.doMove(self.board)
			self.waitForGnuchess = True
		except ValueError as e:
			self["curr_move"].setText("Illegaler Zug")
	
	def receiveAnswer(self, bestmove, ponder):
		"""
		Callback mit einer Antwort von gnuchess.
		Der UCI-Modus liefert immer einen "bestmove" und die erwartete Antwort.
		Diese Antwort wird als "hint" gespeichert und kann über die grüne Taste
		angezeigt werden.
		"""
		self.waitForGnuchess = False
		self.board.push_uci(bestmove)
		if self.flagUndoMove:
			self.undoMove()
			return
		
		self.ponderMove = ponder
		self["curr_move"].setText(bestmove)
		self.showMoves()
		
		if self.board.is_game_over(claim_draw=True):
			self["curr_move"].setText("Spielende")
			self["hint"].setText("Ausgang: "+self.board.result())
			self.isGameOver = True
		elif self.board.is_check():
			self["curr_move"].setText("Schach")
	
	def showMoves(self):
		"""
		Die Liste der Züge kann in maximal vier Spalten angezeigt werden.
		Es wird immer nur die letzte Spalte geschrieben.
		"""
		moves = ""
		column = (len(self.board.move_stack) - 1) / 40
		column = max(0,min(3,column))
		startpos = column * 40
		
		for num, move in enumerate(self.board.move_stack[startpos:]):
			if num % 2 == 0:
				moves += "%+2s. %s " % ( str((num + startpos) / 2 + 1), move.uci() )
			else:
				moves += "%s\n" % move.uci()
		label = "message%d" % column
		self[label].setText(moves)
		# Falls der letzte Zug zurückgenommen wurde und der erste in der
		# neuen Spalte war: auch nächste Spalte anzeigen.
		if column < 3:
			label = "message%d" % (column+1)
			self[label].setText("")
	
	def handlePromotion(self, move_uci):
		"""
		Überprüfen, ob eine Bauern-Umwandlung gemacht werden muss.
		Wenn ja: eine Choice-Box mit den Umwandlungs-Möglichkeiten
		anzeigen. Ein Zug ohne mögliche Umwandlung ist illegal.
		Die korrekte Fortsetzung wird dann aus dem Callback durchgeführt.
		"""
		from_piece = self.board.piece_type_at(self.move[0]) # == 1    -> Bauer
		to_piece = self.board.piece_type_at(self.move[1])   # is None -> leer
		to_line = self.move[1] / 8                          # == 0, 7 -> erste und letzte Reihe
		
		if from_piece == 1 and to_piece is None and to_line in [0,7]:
			# Mögliche Varianten des Zuges mit Umwandlung:
			options = [
				("Dame",     move_uci+"q"),
				("Turm",     move_uci+"r"),
				("Springer", move_uci+"n"),
				("Läufer",   move_uci+"b"),
			]
			self.session.openWithCallback(self.promotionCallback, ChoiceBox,list = options)
			return True
		
		return False
	
	# Den Zug mit der ausgewählten umgewandelten Figur ausführen.
	def promotionCallback(self, ret):
		if ret is not None:
			self["curr_move"].setText("")
			move_uci = ret[1]
			self.playerMove(move_uci)
	
	def undoMove(self):
		self["hint"].setText("")
		try:
			self.board.pop()
			self.board.pop()
		except Exception:
			pass
		self["curr_move"].setText("")
		self["hint"].setText("")
		self.board.drawBoard()
		self.showMoves()
		self.ponderMove = None
		self.flagUndoMove = False
		self.isGameOver = False

	def red(self):
		if self.waitForGnuchess:
			self["hint"].setText("Zug wird zurückgenommen")
			self.flagUndoMove = True
		else:
			self.undoMove()
	
	# Gespeicherten Zug-Vorschlag anzeigen
	def green(self):
		if self.isGameOver:
			return
		if self.ponderMove:
			self["hint"].setText("Vorschlag: %s" % self.ponderMove)
		else:
			self["hint"].setText("Kein Vorschlag vorhanden")
			
	def yellow(self):
		self.whiteBottom = not self.whiteBottom
		self.board.rotateBoard()
	
	# Spieler-Seite wechseln
	def blue(self):
		if self.isGameOver:
			return
		try:
			self.gnuchess.doMove(self.board)
			self["hint"].setText("")
			if self.isWhite:
				self.isWhite = False
				self["player_black"].setText("Spieler")
				self["player_white"].setText("Gnuchess")
				self["key_blue"].setText("Weiß spielen")
				self.board.setFocus(52)
			else:
				self.isWhite = True
				self["player_black"].setText("Gnuchess")
				self["player_white"].setText("Spieler")
				self["key_blue"].setText("Schwarz spielen")
				self.board.setFocus(12)
		except:
			pass

	# Plugin beenden, vorher Gnuchess beenden
	def cancel(self):
		self.gnuchess.quit()
		self.close()
	
	# ---- Logische Feld-Bewegung ---- #
	def moveUp(self):
		if self.whiteBottom:
			self.realMoveUp()
		else:
			self.realMoveDown()

	def moveUpLeft(self):
		if self.whiteBottom:
			self.realMoveUpLeft()
		else:
			self.realMoveDownRight()

	def moveUpRight(self):
		if self.whiteBottom:
			self.realMoveUpRight()
		else:
			self.realMoveDownLeft()

	def moveLeft(self):
		if self.whiteBottom:
			self.realMoveLeft()
		else:
			self.realMoveRight()

	def moveRight(self):
		if self.whiteBottom:
			self.realMoveRight()
		else:
			self.realMoveLeft()

	def moveDown(self):
		if self.whiteBottom:
			self.realMoveDown()
		else:
			self.realMoveUp()

	def moveDownLeft(self):
		if self.whiteBottom:
			self.realMoveDownLeft()
		else:
			self.realMoveUpRight()
	
	def moveDownRight(self):
		if self.whiteBottom:
			self.realMoveDownRight()
		else:
			self.realMoveUpLeft()

	# ---- umgesetzt je nachdem ob Weiß oder Schwarz oben ist ---- #
	# Focus-Feld bewegen
	def realMoveUp(self):
		cellWithFocus = self.board.getFocus() + 8
		if cellWithFocus < 64:
			self.board.setFocus(cellWithFocus)

	def realMoveUpLeft(self):
		cellWithFocus = self.board.getFocus()
		if cellWithFocus % 8 > 0:
			cellWithFocus += 7
			if cellWithFocus < 64:
				self.board.setFocus(cellWithFocus)

	def realMoveUpRight(self):
		cellWithFocus = self.board.getFocus()
		if cellWithFocus % 8 < 7:
			cellWithFocus += 9
			if cellWithFocus < 64:
				self.board.setFocus(cellWithFocus)

	def realMoveLeft(self):
		if self.board.getFocus() % 8 > 0:
			cellWithFocus = self.board.getFocus() - 1
			self.board.setFocus(cellWithFocus)

	def realMoveRight(self):
		if self.board.getFocus() % 8 < 7:
			cellWithFocus = self.board.getFocus() + 1
			self.board.setFocus(cellWithFocus)

	def realMoveDown(self):
		cellWithFocus = self.board.getFocus() - 8
		if cellWithFocus >= 0:
			self.board.setFocus(cellWithFocus)

	def realMoveDownLeft(self):
		cellWithFocus = self.board.getFocus()
		if cellWithFocus % 8 > 0:
			cellWithFocus -= 9
			if cellWithFocus >= 0:
				self.board.setFocus(cellWithFocus)
	
	def realMoveDownRight(self):
		cellWithFocus = self.board.getFocus()
		if self.board.getFocus() % 8 < 7:
			cellWithFocus -= 7
			if cellWithFocus >= 0:
				self.board.setFocus(cellWithFocus)

	# Spielstärke / Bedenkzeit setzen
	def increaseMovetime(self):
		movetime = self.gnuchess.getMovetime()
		if movetime < 10000:
			movetime += 1000
			self.gnuchess.setMovetime(movetime)
			self["hint"].setText("Neue Bedenkzeit: %d Sekunden" % (movetime/1000) )
	
	def decreaseMovetime(self):
		movetime = self.gnuchess.getMovetime()
		if movetime > 1000:
			movetime -= 1000
			self.gnuchess.setMovetime(movetime)
			self["hint"].setText("Neue Bedenkzeit: %d Sekunden" % (movetime/1000) )
