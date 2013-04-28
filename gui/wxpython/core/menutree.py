"""!
@package core.menutree

@brief Creates tree structure for wxGUI menus (former menudata.py)

Classes:
 - menutree::MenuTreeModelBuilder

Usage:
@code
python menutree.py [action] [menu]
@endcode

where <i>action</i>:
 - strings (default, used for translations)
 - tree (simple tree structure)
 - commands (command names and their place in tree)
 - dump (tree structure with stored data)

and <i>menu</i>:
 - manager (Layer Manager)
 - modeler (Graphical Modeler)
 - psmap (Cartographic Composer)

(C) 2013 by the GRASS Development Team

This program is free software under the GNU General Public License
(>=v2). Read the file COPYING that comes with GRASS for details.

@author Glynn Clements (menudata.py)
@author Martin Landa <landa.martin gmail.com> (menudata.py)
@author Anna Petrasova <kratochanna gmail.com>
"""

import os
import sys
import copy
try:
    import xml.etree.ElementTree   as etree
except ImportError:
    import elementtree.ElementTree as etree # Python <= 2.4

import wx

if __name__ == '__main__':
    sys.path.append(os.path.join(os.environ['GISBASE'], "etc", "gui", "wxpython"))
from core.treemodel import TreeModel, ModuleNode
from core.settings import UserSettings

if not os.getenv("GISBASE"):
    sys.exit("GRASS is not running. Exiting...")

class MenuTreeModelBuilder:
    """!Abstract menu data class"""
    def __init__(self, filename):

        self.menustyle = UserSettings.Get(group = 'appearance',
                                          key = 'menustyle',
                                          subkey = 'selection')

        xmlTree = etree.parse(filename)
        self.model = TreeModel(ModuleNode)
        self._createModel(xmlTree)

    def _createModel(self, xmlTree):
        root = xmlTree.getroot()
        menubar = root.findall('menubar')[0]
        menus = menubar.findall('menu')
        for m in menus:
            self._createMenu(m, self.model.root)

    def _createMenu(self, menu, node):
        label = _(menu.find('label').text)
        items = menu.find('items')
        node = self.model.AppendNode(parent=node, label=label)
        for item in items:
            self._createItem(item, node)

    def _createItem(self, item, node):
        if item.tag == 'separator':
            data = dict(label='', description='', handler='',
                        command='', keywords='', shortcut='', wxId='')
            self.model.AppendNode(parent=node, label='', data=data)
        elif item.tag == 'menuitem':
            origLabel = _(item.find('label').text)
            desc     = _(item.find('help').text)
            handler  = item.find('handler').text
            gcmd     = item.find('command')  # optional
            keywords = item.find('keywords') # optional
            shortcut = item.find('shortcut') # optional
            wxId     = item.find('id')       # optional
            if gcmd != None:
                gcmd = gcmd.text
            else:
                gcmd = ""
            if keywords != None:
                keywords = keywords.text
            else:
                keywords = ""
            if shortcut != None:
                shortcut = shortcut.text
            else:
                shortcut = ""
            if wxId != None:
                wxId = eval('wx.' + wxId.text)
            else:
                wxId = wx.ID_ANY
            label = origLabel
            if gcmd:
                if self.menustyle == 1:
                    label += '   [' + gcmd + ']'
                elif self.menustyle == 2:
                    label = '      [' + gcmd + ']'
            data = dict(label=origLabel, description=desc, handler=handler,
                        command=gcmd, keywords=keywords, shortcut=shortcut, wxId=wxId)
            self.model.AppendNode(parent=node, label=label, data=data)
        elif item.tag == 'menu':
            self._createMenu(item, node)
        else:
            raise Exception(_("Unknow tag %s") % item.tag)

    def GetModel(self, separators=False):
        """Returns copy of model with or without separators
        (for menu or for search tree).
        """
        if separators:
            return copy.deepcopy(self.model)
        else:
            model = copy.deepcopy(self.model)
            removeSeparators(model)
            return model

    def PrintTree(self, fh):
        for child in self.model.root.children:
            printTree(node=child, fh=fh)

    def PrintStrings(self, fh):
        """!Print menu strings to file (used for localization)

        @param fh file descriptor
        """
        className = str(self.__class__).split('.', 1)[1]
        fh.write('menustrings_%s = [\n' % className)
        for child in self.model.root.children:
            printStrings(child, fh)
        fh.write('    \'\']\n')

    def PrintCommands(self, fh):
        printCommands(self.model.root, fh, itemSep=' | ', menuSep=' > ')

def removeSeparators(model, node=None):
    if not node:
        node = model.root
    if node.label:
        for child in reversed(node.children):
            removeSeparators(model, child)
    else:
        model.RemoveNode(node)

def printTree(node, fh, indent=0):
    if not node.label:
        return
    text = '%s- %s\n' % (' ' * indent, node.label.replace('&', ''))
    fh.write(text)
    for child in node.children:
        printTree(node=child, fh=fh, indent=indent + 2)

def printStrings(node, fh):
    # node.label  - with module in brackets
    # node.data['label'] - without module in brackets
    if node.label and not node.data:
        fh.write('    _(%r),\n' % str(node.label))
    if node.data:
        if 'label' in node.data and node.data['label']:
            fh.write('    _(%r),\n' % str(node.data['label']))
        if 'description' in node.data and node.data['description']:
            fh.write('    _(%r),\n' % str(node.data['description']))
    for child in node.children:
        printStrings(node=child, fh=fh)

def printCommands(node, fh, itemSep, menuSep):

    def collectParents(node, parents):
        parent = node.parent
        if parent.parent:
            parents.insert(0, node.parent)
            collectParents(node.parent, parents)

    data = node.data
    if data and 'command' in data and data['command']:
        fh.write('%s%s' % (data['command'], itemSep))
        parents = [node]
        collectParents(node, parents)
        labels = [parent.label.replace('&', '') for parent in parents]
        fh.write(menuSep.join(labels))
        fh.write('\n')

    for child in node.children:
        printCommands(child, fh, itemSep, menuSep)


if __name__ == "__main__":
    # i18N
    import gettext
    gettext.install('grasswxpy', os.path.join(os.getenv("GISBASE"), 'locale'), unicode=True)

    action = 'strings'
    menu   = 'manager'

    for arg in sys.argv:
        if arg in ('strings', 'tree', 'commands', 'dump'):
            action =  arg
        elif arg in ('manager', 'modeler', 'psmap'):
            menu = arg

    sys.path.append(os.path.join(os.getenv("GISBASE"), "etc", "gui", "wxpython"))


    if menu == 'manager':
        from lmgr.menudata     import LayerManagerMenuData
        menudata = LayerManagerMenuData()
    elif menu == 'modeler':
        from gmodeler.menudata import ModelerMenuData
        menudata = ModelerMenuData()
    elif menu == 'psmap':
        from psmap.menudata import PsMapMenuData
        menudata = PsMapMenuData()

    if action == 'strings':
        menudata.PrintStrings(sys.stdout)
    elif action == 'tree':
        menudata.PrintTree(sys.stdout)
    elif action == 'commands':
        menudata.PrintCommands(sys.stdout)
    elif action == 'dump':
        print menudata.model

    sys.exit(0)
