from tkinter import *
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox
import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from PIL import Image, ImageTk

import model
import view

class Plugin : #cette classe facilite l'implementation de nouveaux boutons dans le command Panel qui permettent de porposer de nouveaux layers a afficher
    #voir le init pour la signature
    name = None
    function = None
    scrollingMenu = None
    optionList = None
    defaultValues = None

    newWindow = None

    box = None
    current = None
    buttonPlugin = None
    mainFrame = None
    buttonsFrame = None
    labelList = None
    textFieldList = None
    textFieldResultList = None

    def __init__(self, name, rowNumber, function, scrollingMenu, optionList, defaultValues, commandPanel, model):
        #le master est le commandPanel
        #scrollingMenu est une liste de str
        #optionList est une liste de listes, chaque liste correspond aux options de la valeur de scrollingMenu correspondante
        #defaultValues est une liste de listes, dont chaque valeur correspond à la valeur par defaut de l'option de optionList associe

        model.listeners[name] = self

        self.name = name
        self.function = function
        self.scrollingMenu = scrollingMenu
        self.optionList = optionList
        self.defaultValues = defaultValues

        #creation du bouton dans le commandPanel, dont le clic va ouvrir une nouvelle fenetre
        self.buttonPlugin = view.ButtonPlus(commandPanel.commandFrameGrid, text=self.name, command=self.openNewWindow)
        self.buttonPlugin.colors()
        self.buttonPlugin.grid(row=rowNumber,column=0, sticky=W, padx = commandPanel.padLeft, pady = 10)


    def openNewWindow(self):
        #cas ou on a un seul cas dans le menu deroulant et pas d'options : on execute direct la fonction sans ouvrir de fenetre
        if (len(self.scrollingMenu)==0):
            self.function()
        else:
            #creation de la fenetre
            self.newWindow = Tk()
            self.newWindow.title(self.name)
            self.newWindow.geometry("460x300")
            self.newWindow.resizable(False, True)  #on peut etendre la fenetre uniquement selon les y
            self.center(self.newWindow)

            self.newWindow.configure(bg=view.ConstantFiles.lightGrey)
            self.newWindow.update()

            if (os.name=='nt'):
                self.newWindow.iconbitmap(view.ConstantFiles.logoWindows)
            else:
                self.newWindow.iconbitmap(view.ConstantFiles.logoLinux)

            #reinitialisation des attributs, si on ouvre a nouveau la fenetre
            self.box = None
            self.current = None
            self.mainFrame = None
            self.buttonsFrame = None
            self.labelList = None
            self.textFieldList = None
            self.textFieldResultList = None

            #creation du Frame et du titre
            self.mainFrame = Frame(self.newWindow, bg=view.ConstantFiles.lightGrey)
            self.mainFrame.pack(fill=BOTH, expand=True)

            title = Label(self.mainFrame, bg=view.ConstantFiles.lightGrey, font = "Helvetica 11 bold", text=('Enter parameters for ' + self.name))
            title.pack(padx = 5, pady = 10)

            #creation du menu deroulant, vide au depart
            self.box = ttk.Combobox(self.mainFrame, values = self.scrollingMenu, state="readonly")
            self.box.pack(pady=10)
            self.box.bind("<<ComboboxSelected>>", self.newChoice) #appel à chaque changement de choix

            #blocage du bouton de commandPanel pour empecher d'ouvrir une deuxieme fenetre
            self.buttonPlugin['state'] = 'disabled'
            self.newWindow.protocol("WM_DELETE_WINDOW", self.closingWindow)
            self.newWindow.mainloop() #il faut le mettre ici ??

    def closingWindow(self):
        self.buttonPlugin['state'] = 'normal'
        self.newWindow.destroy()


    def newChoice(self, event):
        if (self.buttonsFrame!=None):
            self.buttonsFrame.destroy()

        self.buttonsFrame = Frame(self.mainFrame, bg=view.ConstantFiles.lightGrey)
        self.buttonsFrame.pack()

        self.current = self.box.current() #index de l'option choisie

        options = self.optionList[self.current] #liste d'options du choix selectionné

        self.labelList = []
        self.textFieldList = []

        for i in range(len(options)) :
            optionName = options[i] #optionName est un str

            label = Label(self.buttonsFrame, text=optionName, bg=view.ConstantFiles.lightGrey)
            label.grid(row=i, column=0, sticky=W, padx = 10, pady = 2)
            self.labelList.append(label)

            textField = Entry(self.buttonsFrame)
            textField.insert(END, self.defaultValues[self.current][i]) #valeurs par defaut
            textField.grid(row=i, column=1, sticky=E, padx = 10, pady = 2)
            self.textFieldList.append(textField)

        executeButton = view.ButtonPlus(self.buttonsFrame, text='Execute', command=self.execute)
        executeButton.grid(row=len(options), column=1, sticky=E, padx = 10, pady = 10)

    def execute(self):
        self.textFieldResultList = []
        for textField in self.textFieldList:
            self.textFieldResultList.append(textField.get())

        #gestion des erreurs
        floatFieldResultList = []
        try:
            for text in self.textFieldResultList:
                floatFieldResultList.append(float(text))
                #floatFieldResultList est maintenant une liste de flottants correspondant aux options

        except(ValueError):
            self.failure('Please only write numbers in text fields. Be sure to use a dot "." and not a comma "," for decimals.', False)

        else:
            #on execute donc la fonction du modele
            self.function(self.current, floatFieldResultList)


    def success(self): #cette fonction doit être appele par le modele pour s'executer
        self.newWindow.destroy()
        messagebox.showinfo('Success', 'Your values have been successfuly entered. Click OK to continue and to start the computation.')
        self.buttonPlugin['state'] = 'normal'

    def failure(self, message, close): #cette fonction doit être appele par le modele pour s'executer
        messagebox.showwarning('Error', message)
        if close:
            self.newWindow.destroy()
            self.buttonPlugin['state'] = 'normal'
        else:
            self.newWindow.lift()


    def center(self, win): #cf 'center' de view
        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry('{}x{}+{}+{}'.format(width, height, x, y))