# -*- coding: utf-8 -*-

#
# chess pieces font from https://github.com/xeyownt/chess_merida_unicode
# license: free
#
# TODO:
# - Spielzeit/Uhr als alternative zur Spielstärke
# - Remis anbieten
# - Info-Handler aus chess
# - Absichern, dass gnuchess installiert ist
# - Absichern, dass python-chess installiert ist
# - Ohne Computer spielen
# - Stellung eingeben können
# - Spiel abbrechen/resetten
# - Spiel speichern, laden, fortsetzen
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
		self.engine.terminate()
	
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
		
		self._focusSquare = 12
		
		self._isCastling = False
		self._isEnpassant = False
		
		self.pieceColor = self.boardcolor["black"]
		self.frameColor = self.boardcolor["black"]
	
	def push_uci(self, uci):
		"""
		Überschriebt die Library-Methode, um Rochade und en passant korrekt
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
		return (x * self.cellwidth, (7-y) * self.cellwidth)
	
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
			<panel name="back_top" />
			<panel name="back_top_wide" />
			<panel name="back_bottom_small" />
			<panel name="part_Title" />
			<widget source="Canvas" render="Canvas" position="50,140" size="800,800" />
			<widget name="player_black" position="50,90" size="800,40" font="Regular;30" valign="center" />
			<widget name="player_white" position="50,950" size="800,40" font="Regular;30" valign="center" />
			<widget name="curr_move" position="900,100" size="250,50" font="Regular;35"/>
			<widget name="hint" position="1150,100" size="500,50" font="Regular;35"/>
			<widget name="message0" position="900,175" size="250,800" font="Regular;32"/>
			<widget name="message1" position="1150,175" size="250,800" font="Regular;32"/>
			<widget name="message2" position="1400,175" size="250,800" font="Regular;32"/>
			<widget name="message3" position="1650,175" size="250,800" font="Regular;32"/>
			<widget name="key_red" position="225,1015" size="280,55" zPosition="1" font="Regular; 23" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#00b81c46" />
			<widget name="key_green" position="565,1015" size="280,55" zPosition="1" font="Regular; 23" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#10389416"  />
			<widget name="key_yellow" position="905,1015" size="280,55" zPosition="1" font="Regular; 23" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#109ca81b" />
			<widget name="key_blue" position="1245,1015" size="280,55" zPosition="1" font="Regular; 23" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#008888ff" />
		</screen>
	"""

	def __init__(self, session):
		
		self.session = session
		Screen.__init__(self, session)
		
		self["actions"] =  ActionMap(["ChessboardActions"], {
			"cancel":	   self.cancel,
			"up":		   self.moveUp,
			"down":		   self.moveDown,
			"left":		   self.moveLeft,
			"right":	   self.moveRight,
			"ok":          self.selectSquare,
			"red":		   self.red,
			"green":	   self.green,
			"yellow":	   self.yellow,
			"blue":		   self.blue,
			"nextBouquet": self.increaseMovetime,
			"prevBouquet": self.decreaseMovetime,
		}, -1)
		
		self["Canvas"] = CanvasSource()
		
		self["curr_move"] = Label()
		self["hint"] = Label()
		
		self["message0"] = Label()
		self["message1"] = Label()
		self["message2"] = Label()
		self["message3"] = Label()
		
		self["key_red"] = Label("rot")
		self["key_green"] = Label("Zug vorschlagen")
		self["key_yellow"] = Label("gelb")
		self["key_blue"] = Label("Schwarz spielen")
		
		self["player_black"] = Label("Gnuchess")
		self["player_white"] = Label("Spieler")
		
		self.gnuchess = Gnuchess(self.receiveAnswer)
		self.move  = []
		
		self.isWhite = True
		self.isCheckMate = False
		self.ponderMove = None
		
		self.onLayoutFinish.append(self.setupBoard)
		
	def setupBoard(self):
		self["Canvas"].fill(0,0,800,800, argb(33,255,255,255))
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
		if self.isCheckMate:
			return
		
		self.move.append(self.board.getFocus())
		move_uci = self.getMoveUci()
		self["curr_move"].setText(move_uci)
		if len(self.move) == 2:
			# wenn beide Felder ausgewählt sind, wird der Zug ausgeführt
			move_uci = self.handlePromotion(move_uci)
			self.playerMove(move_uci)

	def playerMove(self, move_uci):
		"""
		Zug des Spielers ausführen.
		Ein illegaler Zug führt zu einer Exception, der Zug wird dann nicht
		weiter ausgeführt
		"""
		try:
			move = self.board.push_uci(move_uci)
			self.showMoves()
			if self.board.is_checkmate():
				self["curr_move"].setText("Schach matt")
				self["hint"].setText("Ausgang: "+self.board.result())
				self.isCheckMate = True
				return
			elif self.board.is_check():
				self["curr_move"].setText("Schach")
			self["hint"].setText("")
			self.gnuchess.doMove(self.board)
		except ValueError as e:
			print e
			self["curr_move"].setText("Illegaler Zug")
		self.move = []
	
	def receiveAnswer(self, bestmove, ponder):
		"""
		Callback mit einer Antwort von gnuchess.
		Der UCI-Modus liefert immer einen "bestmove" und die erwartete Antwort.
		Diese Antwort wird als "hint" gespeichert und kann über die grüne Taste
		angezeigt werden.
		"""
		self.ponderMove = ponder
		self["curr_move"].setText(bestmove)
		move = self.board.push_uci(bestmove)
		self.showMoves()
		
		if self.board.is_checkmate():
			self["curr_move"].setText("Schach matt")
			self["hint"].setText("Ausgang: "+self.board.result())
			self.isCheckMate = True
		elif self.board.is_check():
			self["curr_move"].setText("Schach")
	
	def showMoves(self):
		"""
		Die Liste der Züge kann in maximal vier Spalten angezeigt werden.
		Es wird immer nur die letzte Spalte geschrieben.
		"""
		moves = ""
		column = (len(self.board.move_stack) - 1) / 36
		if column > 3:
			column = 3
		startpos = column * 36
		for num, move in enumerate(self.board.move_stack[startpos:]):
			if num % 2 == 0:
				moves += "%d. %s " % ( (num + startpos) / 2 + 1, move.uci() )
			else:
				moves += "%s\n" % move.uci()
		label = "message%d" % column
		self[label].setText(moves)
	
	def handlePromotion(self, move_uci):
		"""
		Überprüfen, ob eine Bauern-Umwandlung gemacht werden muss.
		Wenn ja: eine Choice-Box mit den Umwandlungs-Möglichkeiten
		anzeigen. Ein Zug ohne mögliche Umwandlung ist illegal.
		Die korrekte Fortsetzung wird dann aus dem Callback durchgeführt.
		"""
		from_piece = self.board.piece_type_at(self.move[0])
		to_piece = self.board.piece_type_at(self.move[1])
		to_line = self.move[1] / 8
		
		if from_piece == 1 and to_piece is None and to_line in [0,7]:
			options = [
				("Dame",move_uci+"q"),
				("Turm",move_uci+"r"),
				("Springer",move_uci+"n"),
				("Läufer",move_uci+"b"),
			]
			self.session.openWithCallback(self.promotionCallback, ChoiceBox,list = options)
		return move_uci
	
	# Den Zug mit der ausgewählten umgewandelten Figur ausführen.
	def promotionCallback(self, ret):
		if ret is not None:
			self["curr_move"].setText("")
			move_uci = ret[1]
			self.playerMove(move_uci)

	def red(self):
		pass
	
	# Gespeicherten Zug-Vorschlag anzeigen
	def green(self):
		if self.isCheckMate:
			return
		if self.ponderMove:
			self["hint"].setText("Vorschlag: %s" % self.ponderMove)
		else:
			self["hint"].setText("Kein Vorschlag vorhanden")
			
	def yellow(self):
		pass
	
	# Spieler-Seite wechseln
	def blue(self):
		try:
			self.gnuchess.doMove(self.board)
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
	
	# Focus-Feld bewegen
	def moveDown(self):
		cellWithFocus = self.board.getFocus() - 8
		if cellWithFocus >= 0:
			self.board.setFocus(cellWithFocus)
			
	def moveUp(self):
		cellWithFocus = self.board.getFocus() + 8
		if cellWithFocus < 64:
			self.board.setFocus(cellWithFocus)
			
	def moveLeft(self):
		if self.board.getFocus() % 8 > 0:
			cellWithFocus = self.board.getFocus() - 1
			self.board.setFocus(cellWithFocus)
			
	def moveRight(self):
		if self.board.getFocus() % 8 < 7:
			cellWithFocus = self.board.getFocus() + 1
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
