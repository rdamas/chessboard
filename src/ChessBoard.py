# -*- coding: utf-8 -*-

from enigma import gFont, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Sources.CanvasSource import CanvasSource   
from Components.Sources.StaticText import StaticText   
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from __init__ import _

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

		self.focusSquare = 12
		self.isCastling = False
		self.isEnpassant = False
		
		self.pieceColor = self.boardcolor["black"]
		self.frameColor = self.boardcolor["black"]
		
	
	def drawCoords(self):
		if self.canvas:
			self.canvas.fill(0, 0, 30, self.cellwidth*8+40, self.boardcolor["light"])
			self.canvas.fill(0, self.cellwidth*8+10, self.cellwidth*8+40, 30, self.boardcolor["light"])
			for coord in range(1,9):
				if self.WhiteBottom:
					hchar = chr(96+coord)  # "a" .. "h"
					vchar = chr(57-coord)  # "8" .. "1"
				else:
					hchar = chr(105-coord) # "h" .. "a"
					vchar = chr(48+coord)  # "1" .. "8"
				offset = (coord-1) * self.cellwidth
				self.canvas.writeText(0, offset, 30, self.cellwidth, 
					self.boardcolor["black"], self.boardcolor["light"],
					gFont("Regular", 24), vchar, 
					RT_HALIGN_CENTER|RT_VALIGN_CENTER)
				self.canvas.writeText(offset+40, self.cellwidth*8+10, self.cellwidth, 30, 
					self.boardcolor["black"], self.boardcolor["light"],
					gFont("Regular", 24), hchar, 
					RT_HALIGN_CENTER|RT_VALIGN_CENTER)
	
	def rotateBoard(self):
		self.WhiteBottom = not self.WhiteBottom
		self.drawCoords()
		self.drawBoard()
	
	def push_uci(self, uci):
		"""
		overrides library method in order to correctly display castling
		and en passant moves on the board. Redraw board now.
		"""
		move = self.parse_uci(uci)
		self.isCastling = self.is_castling(move)
		self.isEnpassant = self.is_en_passant(move)
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
			for square in chess.SQUARES:
				self._drawSquare(square)

	def updateBoard(self, move):
		# if the last move was a castling or en passant move,
		# simply redraw the whole board instead of the fields
		# changed
		if self.isCastling or self.isEnpassant:
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
		if square == self.focusSquare:
			return self.boardcolor["focus"]
		else:
			return self._getBackgroundColor(square)
	
	def _drawSquare(self, square):
		"""
		Draw a cell.
		For the frame draw a cell with black background
		Draw a tiny bit smaller cells with focus and background color onto that
		Last draw the piece using the chess font
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
		oldFocusSquare = self.focusSquare
		self.focusSquare = focusSquare
		self._drawSquare(oldFocusSquare)
		self._drawSquare(focusSquare)
	
	def getFocus(self):
		return self.focusSquare

class MemoryActionMap(ActionMap):
	"""ActionMap that records the key pressed
	"""
	def action(self, contexts, action):
		self.keyPressed = action
		return ActionMap.action(self, contexts, action)

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
		
		self["actions"] =  MemoryActionMap(["ChessboardActions"], {
			"cancel":		self.cancel,
			"up":			self.moveFocus,
			"down":			self.moveFocus,
			"left":			self.moveFocus,
			"right":		self.moveFocus,
			"1":			self.moveFocus,
			"2":			self.moveFocus,
			"3":			self.moveFocus,
			"4":			self.moveFocus,
			"6":			self.moveFocus,
			"7":			self.moveFocus,
			"8":			self.moveFocus,
			"9":			self.moveFocus,
			"5":			self.selectSquare,
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
		
		self["key_red"] = Label(_("Undo move"))
		self["key_green"] = Label(_("Suggest move"))
		self["key_yellow"] = Label(_("Rotate board"))
		self["key_blue"] = Label(_("Play black"))
		
		self["player_black"] = Label(_("Gnuchess"))
		self["player_white"] = Label(_("Player"))
		
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
		Return the two saved moves from self.move[] to UCI notation
		"""
		uci = ""
		for cell in self.move:
			x = cell % 8
			y = cell / 8
			uci += chr(97+x) + chr(49+y)
		return uci

	def selectSquare(self):
		"""
		Event handler for OK key
		The first press saves the field from which to move,
		the second press saves the field where to move.
		"""
		if self.isGameOver:
			return
		
		self.move.append(self.board.getFocus())
		move_uci = self.getMoveUci()
		self["curr_move"].setText(move_uci)
		if len(self.move) == 2:
			# If self.move contains two fields, make the move.
			# A promotion needs be handled separately
			if not self.handlePromotion(move_uci):
				self.playerMove(move_uci)
			self.move = []

	def playerMove(self, move_uci):
		"""
		Make the players move.
		Illegal moves raise an exception, such moves will be aborted.
		"""
		try:
			self.board.push_uci(move_uci)
			self.showMoves()
			if self.board.is_game_over(claim_draw=True):
				self["curr_move"].setText(_("Game over"))
				self["hint"].setText(_("Result: ")+self.board.result())
				self.isGameOver = True
				return
			elif self.board.is_check():
				self["curr_move"].setText(_("Chess"))
			self["hint"].setText("")
			self.gnuchess.doMove(self.board)
			self.waitForGnuchess = True
		except ValueError as e:
			self["curr_move"].setText(_("illegal move"))
	
	def receiveAnswer(self, bestmove, ponder):
		"""
		Callback with answer from gnuchess.
		In UCI mode gnuchess returns a "bestmove" and a "ponder", which is the
		move gnuchess regards as best answer. This move is saved as "hint" and
		can be displayed by pressing the green key.
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
			self["curr_move"].setText(_("Game over"))
			self["hint"].setText(_("Result: ")+self.board.result())
			self.isGameOver = True
		elif self.board.is_check():
			self["curr_move"].setText(_("Chess"))
	
	def showMoves(self):
		"""
		The list of moves can be displayed in maximum 4 columns.
		Always only write the last column...
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
		# ... except the last move was undone. In that case the second last column
		# needs to be displayed as well
		if column < 3:
			label = "message%d" % (column+1)
			self[label].setText("")
	
	def handlePromotion(self, move_uci):
		"""
		Check whether the last move was a promotion.
		If so, show a choice box to select the promotion.
		The move then will be continued from the callback, the return
		from this function will lead to an illegal move, that will
		be ignored
		"""
		from_piece = self.board.piece_type_at(self.move[0]) # == 1    -> piece is a pawn
		to_piece = self.board.piece_type_at(self.move[1])   # is None -> target empty
		to_line = self.move[1] / 8                          # == 0, 7 -> and first or last row of board
		
		if from_piece == 1 and to_piece is None and to_line in [0,7]:
			# list with possible promotions to choose from
			options = [
				(_("Queen"),  move_uci+"q"),
				(_("Rock"),   move_uci+"r"),
				(_("Knight"), move_uci+"n"),
				(_("Bishop"), move_uci+"b"),
			]
			self.session.openWithCallback(self.promotionCallback, ChoiceBox,list = options)
			return True
		
		return False
	
	# Continue the promotion move
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
			self["hint"].setText(_("Move will be undone"))
			self.flagUndoMove = True
		else:
			self.undoMove()
	
	# if we have a move suggestion, display it
	def green(self):
		if self.isGameOver:
			return
		if self.ponderMove:
			self["hint"].setText(_("Sugguested move: %s") % self.ponderMove)
		else:
			self["hint"].setText(_("No move suggestion"))
			
	def yellow(self):
		self.whiteBottom = not self.whiteBottom
		self.board.rotateBoard()
	
	# switch players color
	def blue(self):
		if self.isGameOver:
			return
		try:
			self.gnuchess.doMove(self.board)
			self["hint"].setText("")
			if self.isWhite:
				self.isWhite = False
				self["player_black"].setText(_("Player"))
				self["player_white"].setText(_("Gnuchess"))
				self["key_blue"].setText(_("Play white"))
				self.board.setFocus(52)
			else:
				self.isWhite = True
				self["player_black"].setText(_("Gnuchess"))
				self["player_white"].setText(_("Player"))
				self["key_blue"].setText(_("Play black"))
				self.board.setFocus(12)
		except:
			pass

	# before closing the plugin, gnuchess needs to be terminated
	def cancel(self):
		self.gnuchess.quit()
		self.close()

	# move the focus field
	def moveFocus(self):
		key = self["actions"].keyPressed
		
		# map with move distance for key
		movesWhite = { "1":  7,             "2":  8, "up":    8, "3": 9,
					   "4": -1, "left": -1,                      "right": 1, "6": 1,
					   "7": -9,             "8": -8, "down": -8, "9": -7 }
		movesBlack = { "1": -7,             "2": -8, "up":   -8, "3": -9,
					   "4":  1, "left": 1,                       "right": -1, "6": -1,
					   "7":  9,             "8":  8, "down":  8, "9": 7 }
		
		fOld = fNew = self.board.getFocus()
		if self.whiteBottom:
			dist = movesWhite[key]
			fNew += dist
		else:
			dist = movesBlack[key]
			fNew += dist
		
		# we won't move across the board margin,
		# "mod" is the allowed distance between columns
		if abs(dist) > 1:
			mod = (lambda x: (1, -1)[x<0])(dist)
		else:
			mod = 0
		
		if fNew >= 0 and fNew <= 63 and  fOld / 8 + mod == fNew / 8:
			self.board.setFocus(fNew)

	# change time gnuchess is allowed to compute its next move
	def increaseMovetime(self):
		movetime = self.gnuchess.getMovetime()
		if movetime < 10000:
			movetime += 1000
			self.gnuchess.setMovetime(movetime)
			self["hint"].setText(_("New movetime: %d seconds") % (movetime/1000) )
	
	def decreaseMovetime(self):
		movetime = self.gnuchess.getMovetime()
		if movetime > 1000:
			movetime -= 1000
			self.gnuchess.setMovetime(movetime)
			self["hint"].setText(_("New movetime: %d seconds") % (movetime/1000) )
