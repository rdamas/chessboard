# -*- coding: utf-8 -*-

#
# chess pieces font from https://github.com/xeyownt/chess_merida_unicode
# license: free
#
# TODO:
# - eigene Bauern-Umwandlung (+) - evtl. als SelectList.
# - Spielzeit/Schachuhr
# - Rechenzeit/Schwierigkeitsgrad für gnuchess einstellen
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
		future = self.engine.go(movetime=1000, async_callback=self.received)


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

	# Override, um Rochade und en passant anzeigen zu können
	# Gleich das Board-Update zeichnen
	def push_uci(self, uci):
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
	
	# Eine Zelle zeichnen:
	# Für den Rahmen eine schwarze Zelle
	# Darin eine etwas kleinere Zelle mit der Hintergrundfarbe
	# Darin die Figur
	def _drawSquare(self, square):
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
			<widget source="Canvas" render="Canvas" position="50,140" size="800,800" />
			<widget name="player_black" position="50,90" size="800,40" font="Regular;30" valign="center" />
			<widget name="player_white" position="50,950" size="800,40" font="Regular;30" valign="center" />
			<widget name="runtime" position="1000,100" size="175,50" font="Regular;35"/>
			<widget name="hint" position="1250,100" size="500,50" font="Regular;35"/>
			<widget name="message0" position="1000,175" size="250,800" font="Regular;32"/>
			<widget name="message1" position="1250,175" size="250,800" font="Regular;32"/>
			<widget name="message2" position="1500,175" size="250,800" font="Regular;32"/>
			<widget name="message3" position="1750,175" size="250,800" font="Regular;32"/>
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
			"cancel":	self.cancel,
			"up":		self.moveUp,
			"down":		self.moveDown,
			"left":		self.moveLeft,
			"right":	self.moveRight,
			"ok":       self.markCell,
			"red":		self.red,
			"green":	self.green,
			"yellow":	self.yellow,
			"blue":		self.blue,
		}, -1)
		
		self["Canvas"] = CanvasSource()
		
		self["runtime"] = Label()
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
		self.moves = []
		
		self.isWhite = True
		self.isCheckMate = False
		self.ponderMove = None
		
		self.onLayoutFinish.append(self.setupBoard)
		
	def setupBoard(self):
		self["Canvas"].fill(0,0,800,800, argb(33,255,255,255))
		self.board = ChessBoard(canvas=self["Canvas"])
		self.board.drawBoard()

	def getNotation(self):
		notation = ""
		for cell in self.move:
			x = cell % 8
			y = cell / 8
			notation += chr(97+x) + chr(49+y)
		return notation

	# mit dem ersten ok-Klick wird die Figur gemerkt,
	# mit dem zweiten Klick gezogen
	def markCell(self):
		if self.isCheckMate:
			return
		
		self.move.append(self.board.getFocus())
		self["runtime"].setText(self.getNotation())
		if len(self.move) == 2:
			try:
				data = self.getNotation()
				move = self.board.push_uci(data)
				self.moves.append(data)
				self.showMoves()
				if self.board.is_checkmate():
					self["runtime"].setText("Schach matt")
					self.isCheckMate = True
					return
				elif self.board.is_check():
					self["runtime"].setText("Schach")
				self["hint"].setText("")
				self.gnuchess.doMove(self.board)
			except ValueError:
				self["runtime"].setText("Illegaler Zug")
			self.move = []
	
	# Callback von Gnuchess
	def receiveAnswer(self, bestmove, ponder):
		self.ponderMove = ponder
		self["runtime"].setText(bestmove)
		move = self.board.push_uci(bestmove)
		self.moves.append(bestmove)
		self.showMoves()
		
		if self.board.is_checkmate():
			self.isCheckMate = True
			self["runtime"].setText("Schach matt")
		elif self.board.is_check():
			self["runtime"].setText("Schach")
	
	# Liste der Züge in maximal drei Spalten anzeigen
	# Es wird immer nur die letzte Spalte geschrieben
	def showMoves(self):
		moves = ""
		column = (len(self.moves) - 1) / 36
		startpos = column * 36
		for num, move in enumerate(self.moves[startpos:]):
			if num % 2 == 0:
				moves += "%d. %s " % ( (num + startpos) / 2 + 1, move )
			else:
				moves += "%s\n" % move
		label = "message%d" % column
		self[label].setText(moves)
	
	def red(self):
		pass
	
	def green(self):
		if self.ponderMove:
			self["hint"].setText("Vorschlag: %s" % self.ponderMove)
		else:
			self["hint"].setText("Kein Vorschlag vorhanden")
			
	def yellow(self):
		pass
	
	def blue(self):
		if self.isWhite:
			self.isWhite = False
			self["player_black"].setText("Spieler")
			self["player_white"].setText("Gnuchess")
			self.board.setFocus(52)
			self.gnuchess.doMove(self.board)
		pass

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