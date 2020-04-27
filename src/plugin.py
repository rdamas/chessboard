# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
import ChessBoard

from enigma import addFont

addFont(resolveFilename(SCOPE_PLUGINS, "Extensions/ChessBoard/font/") + "chess_merida_unicode.ttf", "chess", 100, False)

def main(session, **kwargs):
	reload(ChessBoard)
	try:
		session.open(ChessBoard.Board)
	except:
		import traceback
		traceback.print_exc()

def Plugins(**kwargs):
	return PluginDescriptor(
		name="ChessBoard", 
		description="Gnuchess Frontend",
		where = PluginDescriptor.WHERE_PLUGINMENU, 
		fnc=main)
