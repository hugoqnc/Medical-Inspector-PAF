from tkinter import *
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox
import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from PIL import Image, ImageTk

import plugin

class View :
    window = None
    model = None

    def __init__(self, window, model) :
        self.window = window
        self.model = model

        ConstantFiles.start() #initialise les constantes utilisees

        Home(self)

class Home: #home est la classe superieure de view, qui va creer les instances necessaires
    model = None #home stocke le model, et les classes inferieures vont garder une reference sur home et donc sur le model
    window = None
    homeFrame = None
    imagePanel = None #a gauche de l'app, contient toute la partie image
    commandPanel = None #a droite de l'app, contient toute la partie commande
    windowHeight = None
    popup = None


    def __init__(self, master):
        self.window = master.window
        self.model = master.model
        self.windowHeight = self.window.winfo_height()

        self.homeFrame = Frame(self.window, bg='black')
        self.homeFrame.pack(expand=True, fill=BOTH)

        self.popup = Popup(self)

        self.imagePanel = ImagePanel(self.homeFrame, self) #creation du contenu de la fenetre
        self.commandPanel = CommandPanel(self.homeFrame, self)

    def updateImagePanel(self): #permet de reconstruire l'imagePanel, on l'utilise lorsque qu'il y a un gros changement pour ne pas avoir a refresh les widgets individuellement
        self.imagePanel.imageFrame.destroy()
        self.imagePanel = ImagePanel(self.homeFrame, self)


        #apres avoir tout supprime et reconstruit, il faut re faire apparaitre le slider alpha si le bouton de segmentation est encore enfonce
        #on est oblige de faire ce cas manuellement car c'est le seul element de imagePanel qui est construit par le commandPanel
        if (self.model.layerSet[1]==True): #si c'est la segmentation, afficher le curseur alpha
            self.commandPanel.layerOptionsFrame.sliderAlphaLabel = Label(self.imagePanel.imageFrame, text='Alpha Transparency Slider', font = "Helvetica 10", bg=ConstantFiles.darkGrey, fg='white')
            self.commandPanel.layerOptionsFrame.sliderAlphaLabel.pack()
            self.commandPanel.layerOptionsFrame.sliderAlpha = Scale(self.imagePanel.imageFrame,  from_=0, to=1, resolution=0.01, length = ConstantFiles.sliderSize, orient=HORIZONTAL, bg=ConstantFiles.darkGrey, fg='white', troughcolor=ConstantFiles.middleGrey, highlightthickness=0, command=self.model.setAlpha)
            self.commandPanel.layerOptionsFrame.sliderAlpha.set(self.model.alpha) #regle la valeur initiale du slider
            self.commandPanel.layerOptionsFrame.sliderAlpha.pack()

        return

    def updateCommandPanel(self): #inutilisee actuellement, mais permet de reinitiliser completement le commandPanel
        self.commandPanel.commandFrame.destroy()
        self.commandPanel = CommandPanel(self.homeFrame, self)
        return



class ImagePanel:

    imageFrame = None #Frame qui contient toute la suite
    imageSize = None #taille en pixels du canvas qui contient l'image
    slider = None #reference sur le slider en Z
    home = None
    canvas = None #canvas qui contient l'image
    regionLabel = None #label en bas à gauche de l'image qui affiche la region de segmentation et les coordonnes matricielles
    rotation = 0 #on tourne l'image de rotation*90 degres, avec rotation=0,1,2,3
    zoomState = 0 #vaut 0 sans zoom, 1 si on est en mode zoom sur l'image
    zoomBox = [0,0,0,0] #stocke les coordonnes des 2 points qui forment le rectangle sur lequel on zoom

    title3DImages = None #references sur les labels du haut de l'imagePanel
    titleSegmentation = None
    titleGraph = None

    def __init__(self, master, home):
        self.home = home

        #La vue se déclare auprès du modele
        self.home.model.listeners['imagePanel'] = self

        #creation du frame principal
        self.imageFrame = Frame(master, bg=ConstantFiles.darkGrey)
        self.imageFrame.pack(fill=BOTH, expand=True, side=RIGHT)

        #top of the view
        topFrame = Frame(self.imageFrame, bg=ConstantFiles.darkGrey)
        topFrame.pack(pady=10)

        if(home.model.fileName==''): #disjonction de cas sur l'affichage du label au dessus de l'image
            self.title3DImages = Label(topFrame, bg=ConstantFiles.darkGrey, font = "Helvetica 12 bold", fg='red', text=('No 3D Medical Images'))
        else :
            self.title3DImages = Label(topFrame, bg=ConstantFiles.darkGrey, font = "Helvetica 12 bold", fg='white', text=('3D Medical Images : ' + home.model.fileName))
        self.title3DImages.grid(row=0,column=0, sticky=W, padx = 10)

        if(home.model.segPath=='generated' and home.model.segFileName==''): #disjonction de cas sur l'affichage du label au dessus de l'image
            self.titleSegmentation = Label(topFrame, bg=ConstantFiles.darkGrey, font = "Helvetica 12 bold", fg='yellow', text=('Segmentation : Generated [unsaved]'))
        elif(home.model.segFileName==''):
            self.titleSegmentation = Label(topFrame, bg=ConstantFiles.darkGrey, font = "Helvetica 12 bold", fg='red', text=('No Segmentation'))
        else :
            self.titleSegmentation = Label(topFrame,  bg=ConstantFiles.darkGrey, font = "Helvetica 12 bold", fg='white', text=('Segmentation : ' + home.model.segFileName))
        self.titleSegmentation.grid(row=1,column=0, sticky=W, padx = 10, pady = 10)

        if(home.model.graphPath=='generated' and home.model.graphFileName==''): #disjonction de cas sur l'affichage du label au dessus de l'image
            self.titleGraph = Label(topFrame, bg=ConstantFiles.darkGrey, font = "Helvetica 12 bold", fg='yellow', text=('Graph : Generated [unsaved]'))
        elif(home.model.graphFileName==''):
            self.titleGraph = Label(topFrame, bg=ConstantFiles.darkGrey, font = "Helvetica 12 bold", fg='red', text=('No Graph'))
        else :
            self.titleGraph = Label(topFrame,  bg=ConstantFiles.darkGrey, font = "Helvetica 12 bold", fg='white', text=('Graph : ' + home.model.graphFileName))
        self.titleGraph.grid(row=2,column=0, sticky=W, padx = 10)


        #creation de boutons pour adapter la taille de l'image, et pour rotationner l'image
        refreshButton = ButtonPlus(topFrame, text='refresh', image = ConstantFiles.icoSizeRefresh,  command=(lambda: self.refreshCanvasSize()))
        refreshButton.grid(row=0,column=1, sticky=E, padx = 10)

        rotateButton = ButtonPlus(topFrame, text="rotate", image = ConstantFiles.icoRotate, command=(lambda: self.displayRotatedImage()))
        rotateButton.grid(row=1,column=1, sticky=E, padx = 10)

        self.imageSize = int((1/2)*self.home.windowHeight)


        #Middle of the view
        middleFrame = Frame(self.imageFrame, bg=ConstantFiles.darkGrey)
        middleFrame.pack(pady=0)

        self.canvas = Canvas(middleFrame, width = self.imageSize, height = self.imageSize, cursor='plus', bg=ConstantFiles.darkGrey, highlightbackground=ConstantFiles.darkGrey)
        #on cree le label qui affichera le num de la region :
        self.regionLabel = Label(middleFrame, bg=ConstantFiles.darkGrey, font = "Helvetica 10", fg='black', text=('Region : '))

        self.canvas.bind('<Button-1>', self.zoomIn) #relie les clicks sur l'image aux actions donnes dans le manuel utilisateur
        self.canvas.bind('<Button-2>', self.zoomOut)
        self.canvas.bind('<Leave>', self.hideDisplayLabel)
        self.canvas.bind('<Motion>', self.showDisplayLabel)
        self.canvas.grid(row=0,column=0, sticky=W, padx = 0)
        self.regionLabel.grid(row=1,column=0, sticky=W, padx = 0)

        #calculs pour le premier affichage de l'image, segmentation et graph
        self.home.model.sliderValue = 0
        self.home.model.createBgMat(self.home.model.path, self.home.model.fileName)
        self.home.model.createSegmentationMat(self.home.model.segPath, self.home.model.segFileName)
        self.home.model.createGraph(self.home.model.graphPath, self.home.model.graphFileName)

        #creation des sliders verticaux de reglage du contraste
        sliderWLFrame = Frame(middleFrame, bg=ConstantFiles.darkGrey)
        sliderWLFrame.grid(row=0,column=1, sticky=W, padx = 5)

        self.sliderWindowW = Scale(sliderWLFrame, from_=self.home.model.windowLMax - self.home.model.windowLMin, to=1, length = ConstantFiles.sliderSize, orient=VERTICAL, showvalue = 1, bg=ConstantFiles.darkGrey, fg='white', troughcolor=ConstantFiles.middleGrey, highlightthickness=0, command=self.home.model.setWindowW)
        self.sliderWindowW.set(self.home.model.windowW)
        self.sliderWindowW.grid(row=1,column=0, sticky=W, padx = 0)

        self.sliderWindowL = Scale(sliderWLFrame, from_=self.home.model.windowLMax, to=self.home.model.windowLMin, length = ConstantFiles.sliderSize, orient=VERTICAL, showvalue = 1, bg=ConstantFiles.darkGrey, fg='white', troughcolor=ConstantFiles.middleGrey, highlightthickness=0, command=self.home.model.setWindowL)
        self.sliderWindowL.set(self.home.model.windowL)
        self.sliderWindowL.grid(row=1,column=1, sticky=W, padx = 0)

        labelW = Label(sliderWLFrame, text='W', bg=ConstantFiles.darkGrey, fg='white')
        labelW.grid(row=0,column=0, sticky=N, pady = 2)

        labelL = Label(sliderWLFrame, text='L', bg=ConstantFiles.darkGrey, fg='white')
        labelL.grid(row=0,column=1, sticky=N, pady = 2)

        #Bottom  of the view

        #Zslider :
        longFrame = Frame(self.imageFrame, bg=ConstantFiles.darkGrey)
        longFrame.pack(pady=10, padx=10)

        self.slider = Scale(longFrame, from_=0, to=self.home.model.maxZ, length = ConstantFiles.sliderSize, orient=HORIZONTAL, bg=ConstantFiles.darkGrey, fg='white', troughcolor=ConstantFiles.middleGrey, highlightthickness=0, command=self.home.model.setSliderValue)
        self.slider.grid(row=0,column=0, sticky=E, padx = 3)

        #bouton aide qui ouvre une fenetre avec le manuel
        helpButton = ButtonPlus(longFrame, text='help', image=ConstantFiles.icoHelp,  command=(lambda: self.showMeHelp()))
        helpButton.grid(row=0,column=1, sticky=W, padx = (30,10))

        sep = ttk.Separator(self.imageFrame, orient="horizontal") #separateur
        sep.pack(anchor="nw", fill=X, padx=20, pady=15)



    def showMeHelp(self): #affiche la fentre d'aide avec le manuel utilisateur
        #c'est le contenu de cette fonction qu'il faut modifier si on souhaite modifier le manuel utilisateur

        #creation de la fenetre
        newWindow = Tk()
        newWindow.title('User Manual - Medical Inspector 3D')
        newWindow.geometry("540x400")
        newWindow.resizable(True, True)  #on peut etendre la fenetre
        self.center(newWindow) #centre la fenetre dans l'ecran avec une fonction custom

        newWindow.configure(bg='white')
        newWindow.update()

        if (os.name=='nt'): #affichage de l'icone de l'app (ne marche malheureusement pas sous linux)
            newWindow.iconbitmap(ConstantFiles.logoWindows)
        else:
            newWindow.iconbitmap(ConstantFiles.logoLinux)

        #parametres
        S = Scrollbar(newWindow) #fentre deroulante avec une barre de defilement sur la droite
        T = Text(newWindow, wrap=WORD)
        S.pack(side=RIGHT, fill=Y, padx = 20, pady = 20)
        T.pack(side=LEFT, fill=Y, padx = 20, pady = 20)
        S.config(command=T.yview)
        T.config(yscrollcommand=S.set)

        #styles
        T.tag_configure('first', font=('Arial', 20, 'bold'))
        T.tag_configure('title', font=('Arial', 16, 'bold'))
        T.tag_configure('paragraph', font=('Arial', 12, 'bold'))
        T.tag_configure('body', font=('Arial', 10))
        T.tag_configure('credits', font=('Arial', 10, 'italic'))

        #contenu - il faut modifier ici le texte du guide
        content0 = '\n    User Manual\n\n'
        T.insert(END, content0, 'first')

        content0 = '\nThe command options\n'
        T.insert(END, content0, 'title')

        content1 = '\nHow to load a file\n'
        T.insert(END, content1, 'paragraph')

        content2 = 'You can load a 3D Medical Image (.ni.gz), a segmentation (.ni.gz) and a graph (.json) with the 3 load buttons on the Commands panel. You also can unload these files by clicking the X icon next to the load button.'
        T.insert(END, content2, 'body')

        content3 = '\nHow to generate a file\n'
        T.insert(END, content3, 'paragraph')

        content4 = 'To generate a segmentation, graph or cluster, you first need to have a loaded 3D image file. You can then generate the file you need by clicking the appropriate button, and following the window instructions. Once you clicked on "Generate", you will need to wait a moment until the generation is actually done. To generate a graph, you will need to have a loaded segmentation, and to generate a cluster, you will need to have a loaded graph. You can then save these files using the save icon next to the corresponding load button.'
        T.insert(END, content4, 'body')

        content = '\nHow to display the segmentation or graph\n'
        T.insert(END, content, 'paragraph')

        content = 'First click on the layers option button, and 3 other buttons will appear below. The first one enables the 3D Medical Image, the second one the segmentation and the third one the graph. You can select a combination of your choice between these buttons. To mask these options, just click the layer options button again.'
        T.insert(END, content, 'body')

        content = '\nHow to change the transparency of the segmentation\n'
        T.insert(END, content, 'paragraph')

        content = 'Be sure to have the segmentation button from the layers options panel checked. You will see a slider below the image, that will allow you to vary the transparency level of the segmentation.'
        T.insert(END, content, 'body')

        content = '\n\nThe top of the window\n'
        T.insert(END, content, 'title')

        content = '\nThe Size button\n'
        T.insert(END, content, 'paragraph')

        content = 'The size button allows you to see your image at the best possible size depending on the window size. For example, if you extend the window, just click the Size button to make your image bigger. It also works the other way around.'
        T.insert(END, content, 'body')

        content = '\nThe Rotate button\n'
        T.insert(END, content, 'paragraph')

        content = 'The rotate button allows you to rotate your image from 90° to the right. Click again and it will rotate to 180°, then 270°, and it will then come back to 0°.'
        T.insert(END, content, 'body')

        content = '\nThe 3 texts\n'
        T.insert(END, content, 'paragraph')

        content = 'You will see 3 texts on the top of the window. They display the state of the 3D Medical Image file, the Segmentation file and the graph file. They can appear white, red or yellow. If a file is loaded from your file explorer, the text will appear white. If there is no file loaded, the text will appear red. And if the file has been generated from the 3D Medical Image, the text will appear yellow. In this case, you will also be able to know if your generated file has been saved or not.'
        T.insert(END, content, 'body')

        content = '\n\nThe image canvas and options\n'
        T.insert(END, content, 'title')

        content = '\nHow to navigate through space\n'
        T.insert(END, content, 'paragraph')

        content = 'Your canvas will display a 2D slice image from the loaded 3D Medical Image file. But you can navigate in the z axis using the slider below the image.'
        T.insert(END, content, 'body')

        content = '\nHow to read the graph\n'
        T.insert(END, content, 'paragraph')

        content = 'The graph shows the nodes in the slice you are currently looking at. It also shows the link between the nodes, in yellow or red. If the link is yellow, it means that the node is connected to another node above. If the link is red, it means that the node is connected to another node below. The thickness of a link is porportionnal to the ressemblance between the 2 connected nodes.'
        T.insert(END, content, 'body')

        content = '\nHow to zoom\n'
        T.insert(END, content, 'paragraph')

        content = 'To zoom on the image, just left click on the point where you want to zoom. You will enter "zoom mode", and you can navigate through the zoomed image by clicking on where you want to go. To exit zoom mode, just right click somewhere on the image.'
        T.insert(END, content, 'body')

        content = '\nHow to know your position in the matrix\n'
        T.insert(END, content, 'paragraph')

        content = 'If you move your mouse over the image, your i,j,k position in the 3D image matrix will appear on the left below the image. If you also have a loaded segmentation, you will know the levels of segmentation zones through the same text.'
        T.insert(END, content, 'body')

        content = '\nHow to set the contrast (W & L)\n'
        T.insert(END, content, 'paragraph')

        content = 'The contrast of your image can be set through the W and L sliders ont the right of the image. This can allow you to see the best details of your high dynamic range medical image. The Level (L) corresponds to the pixel value that corresponds to the mid-gray brightness level on the monitor. Increasing the level will make the image darker, whereas decreasing the level value will make the image brighter. The window Width (W) determines the range of pixel values that will be incorporated into the display width. Increasing W will reduce display contrast whereas decreasing the W increases the brightness interval between two consecutive pixel values.'
        T.insert(END, content, 'body')

        content = '\n\nPlugins\n'
        T.insert(END, content, 'title')

        content = '\nWhat are plugins in Medical Inspector 3D\n'
        T.insert(END, content, 'paragraph')

        content = 'In this software, you can use plugins to add some new methods of segmentation, graph generation or graph clustering. This can be achieved by changing the current "Generate" buttons, or by creating new ones."\n'
        T.insert(END, content, 'body')

        content = '\nHow to create a plugin\n'
        T.insert(END, content, 'paragraph')

        content = 'You first need to create a new instance of the Plugin class in view.py, inside the commandPanel. You will have to use the following signature :  Plugin(name, rowNumber, function, scrollingMenu, optionList, defaultValues, commandPanel, model). This will automatically create a button in the command panel, which will open a new window with the options you need. You will need to provide a function that is executed after choosing the options. We advise you to write this function in the model.py. You will find more information in the Plugin class (in plugin.py).'
        T.insert(END, content, 'body')

        content = '\n\n\nPAF 2020 - Télécom Paris\n'
        T.insert(END, content, 'credits')

        content = 'Anna Audit - Clément Galaup - Hugo Queinnec - Nicolas Wittmann - Philippe Liu - Pierre Piovesan -Thomas Poyet\n'
        T.insert(END, content, 'credits')

        T.config(state=DISABLED) #empeche la modification du texte

        newWindow.mainloop()

        return


    def center(self, win): #fonction custom pour centrer une fentre dans l'ecran
        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry('{}x{}+{}+{}'.format(width, height, x, y))


    def refreshCanvasSize(self): #rafraichit le taille du canvas par rapport à la taille de la fenetre
        self.home.window.update()
        self.home.windowHeight = self.home.window.winfo_height()
        self.imageSize = int((1/2)*self.home.windowHeight) #la taille du canvas prend la moitie de la hauteur de la fenetre
        self.canvas.config(width = self.imageSize, height = self.imageSize)
        self.displayImage()
        return


    def displayImage(self): #fonction appellee pour afficher l'image sur le canvas. Actuellement, cela ne focntionne qu'avec des images carrees
        #l'image est donne par le model et s'appelle displayedImage

        if(self.zoomState==1): #gere l'affichage lorsque le zoom est active
            image = self.home.model.displayedImg.resize((self.imageSize, self.imageSize)).rotate(self.rotation*(-90))
            self.canvas.image = ImageTk.PhotoImage(image = image.resize((self.imageSize, self.imageSize), box=self.zoomBox))
            self.canvas.create_image(self.imageSize/2,self.imageSize/2, image=self.canvas.image)
        else:
            self.canvas.image = ImageTk.PhotoImage(image = self.home.model.displayedImg.resize((self.imageSize, self.imageSize), Image.LANCZOS).rotate(self.rotation*(-90)))
            self.canvas.create_image(self.imageSize/2,self.imageSize/2, image=self.canvas.image)

        return

    def displayRotatedImage(self): #gere l'etat de la rotation, et affiche l'image
        self.rotation+=1
        if(self.rotation==4):
            self.rotation=0
        self.displayImage()


    def zoomIn(self, event): #fonction de zoom appellee par un clic gauche sur le canvas

        x = event.x
        y = event.y
        k = ConstantFiles.zoomFactor #facteur de zoom >1

        self.hideDisplayLabel(event) #POur cacher le coin quand on zoom

        if(self.zoomState==1): #cas ou on click alors que l'image est deja zoomee (change les x et y pour correspondre a la realite)
            box = self.zoomBox
            oldX = (box[0]+box[2])/2
            oldY = (box[1]+box[3])/2
            x = oldX + (x - oldX)/k
            y = oldY + (y - oldX)/k

        #cas normal : calcul des 4 coordonnes du rectangle de zoom
        x1 = int(x-(self.imageSize/(2*k)))
        y1 = int(y-(self.imageSize/(2*k)))
        x2 = int(x+(self.imageSize/(2*k)))
        y2 = int(y+(self.imageSize/(2*k)))

        #modifie ces coordonnees si elles sortent du cadre de l'image
        if(x1<0):
            x2 = x2 - x1
            x1 = 0
        if(y1<0):
            y2 = y2 - y1
            y1 = 0
        if(x2>self.imageSize):
            x1 = x1 - (x2-self.imageSize)
            x2 = self.imageSize
        if(y2>self.imageSize):
            y1 = y1 - (y2-self.imageSize)
            y2 = self.imageSize

        self.zoomState = 1
        self.zoomBox = [x1, y1, x2, y2]
        self.displayImage() #displayImage va gere l'affichage du zoom

        return


    def zoomOut(self, event): #dezoom si on click droit sur l'image
        self.zoomState = 0
        self.displayImage()
        return

    def hideDisplayLabel(self, event) : #On sort du canvas donc on cache la zone ou on affiche le label avec la region de segmentation et les coordonnees
        self.regionLabel['bg'] = ConstantFiles.darkGrey
        self.regionLabel.grid()


    def showDisplayLabel(self, event) : #La souris se déplace sur le canva on met a jour la valeur du label avec la region de segmentation et les coordonnees
        height = self.imageSize
        width = self.imageSize #image necessairement carree pour l'instant

        if (self.zoomState == 0) :
            x = event.x
            y = event.y
            if self.rotation == 0 :
                a = x #a et b sont les coords en annulant la rotation
                b = y
            elif self.rotation == 1 :
                a = y
                b = height - x
            elif self.rotation == 2 :
                a = width - x
                b = height - y
            else :
                a = width - y
                b = x

            #a indique la colonne et b la ligne
            i = int(b/height * (self.home.model.shape[0] - 1))
            j = int(a/width * (self.home.model.shape[1] - 1))
            k = self.home.model.sliderValue

            try:
                pointedRegion = self.home.model.segmentation[i, j, k]
            except:
                pointedRegion = 0.0

            self.regionLabel['text'] = 'Region : ' + str(pointedRegion) + " (i = " + str(i) + ', j = ' + str(j) + ", k = " + str(k) + ')'
            self.regionLabel['bg'] = 'white'
            self.regionLabel.grid()


class CommandPanel:

    commandFrame = None #frame principale qui va contenir les boutons
    commandFrameGrid = None #frame inferieure qui sera mise en forme par un .grid()
    layerOptionsFrame = None #frame tout en bas qui va contenir les options de segmentation
    home = None
    padLeft = 15 #valeur du padding telle que tous les boutons aient la meme valeur a gauche de la fenetre

    def __init__(self, master, home):

        self.home = home

        #La vue se déclare auprès du modele
        self.home.model.listeners['commandPanel'] = self

        #creation des frames
        self.commandFrame = Frame(master, bg=ConstantFiles.lightGrey)
        self.commandFrame.pack(fill = BOTH, side = LEFT,pady = 30, padx = 30)

        self.layerOptionsFrame = LayerButtons(self.commandFrame, home)

        self.commandFrameGrid = Frame(self.commandFrame, bg=ConstantFiles.lightGrey)
        self.commandFrameGrid.pack()

        #titre
        title = Label(self.commandFrameGrid, text='Commands', font = "Helvetica 16 bold", bg=ConstantFiles.lightGrey)
        title.grid(row=0,column=0, sticky=W, padx = 40, pady=20)

        #creation des boutons
        #on utilise un Frame dans lequel on peut mettre un boutons, plus 2 boutons pour save et delete a droite du bouton principal
        b1Frame = Frame(self.commandFrameGrid, bg=ConstantFiles.lightGrey) #1ere ligne de boutons
        b1Frame.grid(row=1,column=0, sticky=W, padx = self.padLeft-7, pady = 10)

        b1 = ButtonPlus(b1Frame, text="Load 3D Image", command=(lambda :self.load3DImage()))
        b1.colors() #affiche les bonnes couleurs pour le bouton
        b1.grid(row=0,column=0, sticky=W, padx=7)

        b1Del = ButtonPlus(b1Frame, text="X", image=ConstantFiles.icoCross, command=(lambda :self.remove3DImage()))
        b1Del.colors()
        b1Del.grid(row=0,column=2, sticky=W, padx = 0)


        b2Frame = Frame(self.commandFrameGrid, bg=ConstantFiles.lightGrey) #2eme ligne de boutons
        b2Frame.grid(row=2,column=0, sticky=W, padx = self.padLeft-7, pady = 10)

        b2 = ButtonPlus(b2Frame, text="Load Segmentation", command=(lambda :self.loadSegmentation()))
        b2.colors()
        b2.grid(row=0,column=0, sticky=W, padx=7)

        b2Save = ButtonPlus(b2Frame, text="S", image=ConstantFiles.icoSave, command=(lambda :self.saveSegmentation()))
        b2Save.colors()
        b2Save.grid(row=0,column=1, sticky=W, padx = 0)

        b2Del = ButtonPlus(b2Frame, text="X", image=ConstantFiles.icoCross, command=(lambda :self.removeSegmentation()))
        b2Del.colors()
        b2Del.grid(row=0,column=2, sticky=W, padx = 0)


        b3Frame = Frame(self.commandFrameGrid, bg=ConstantFiles.lightGrey) #3eme ligne de boutons
        b3Frame.grid(row=3,column=0, sticky=W, padx = self.padLeft-7, pady = 10)

        b3 = ButtonPlus(b3Frame, text="Load Graph", command=(lambda :self.loadGraph()))
        b3.colors()
        b3.grid(row=0,column=0, sticky=W, padx=7)

        b3Save = ButtonPlus(b3Frame, text="S", image=ConstantFiles.icoSave, command=(lambda :self.saveGraph()))
        b3Save.colors()
        b3Save.grid(row=0,column=1, sticky=W, padx = 0)

        b3Del = ButtonPlus(b3Frame, text="X", image=ConstantFiles.icoCross, command=(lambda :self.removeGraph()))
        b3Del.colors()
        b3Del.grid(row=0,column=2, sticky=W, padx = 0)


        #apres les 3 premieres lignes de boutons, s'ajoutent les boutons de plugin
        #on cree automatiquement un bouton en creant une instance de Plugin
        plugin.Plugin('Generate Segmentation', 4, self.home.model.segmentationPlugin, ['SLIC3D', 'WatershedGradient3D', 'WatershedMinima3D', 'Watervoxel3D'], [['Number of segments (integer)', 'Sigma (decimal)'], ['Gradient Threshold (integer)', 'Gradien Size (integer)', 'Footprint Median (integer)'], ['Footprint Gaussian (integer)', 'Sigma (decimal)'], ['a ∈ ]0,1[ (decimal)', 'Gradient Threshold (integer)', 'Gradient Size (integer)', 'Footprint Median (integer)', 'Footprint Gaussian (integer)', 'Sigma (decimal)']], [[5000, 0.01], [18, 5, 1], [20, 0.5], [0.9, 18, 5, 1, 25, 0.5]], self, self.home.model)
        plugin.Plugin('Generate Graph', 5, self.home.model.graphGenerationPlugin, ['Mean Color', 'Boundary'], [['Sigma (decimal)', 'Draw graph (0 if no)'], ['Sigma (decimal)', 'Draw graph (0 if no)']], [[2500, 1], [2500, 1]], self, self.home.model)
        plugin.Plugin('Generate Clusters', 6, self.home.model.graphClusteringPlugin, ['Louvain', 'Spectral Clustering'], [[], ['Number of clusters (int)']], [[], [80]], self, self.home.model)


        #dernier bouton, qui permet d'afficher les options de layer
        bX = ButtonPlus(self.commandFrameGrid, text="Layer Options", command=(lambda :self.layerOptionsFrame.showLayerOptions(bX)))
        bX.colors()
        #bX.grid(row=7,column=0, sticky=W, padx = self.padLeft, pady = 10)
        self.layerOptionsFrame.showLayerOptions(bX) #macOS version




    def load3DImage(self):
        #ouvre une fenetre de dialogue pour ouvrir un fichier du bon format
        completePath = filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = (("nii files","*.gz"),("all files","*.*")))
        if (completePath == ''): #cas ou on clique sur la croix de la fenetre et ou aucun chemin n'est rentre
            return
        else:
            try:
                (path, fileName) = os.path.split(completePath)
            except TypeError:
                pass
            else:
                self.home.model.createBgMat(path, fileName)
                self.home.updateImagePanel()
        return

    def loadSegmentation(self):
        #ouvre une fenetre de dialogue pour ouvrir un fichier du bon format
        completePath = filedialog.askopenfilename(initialdir = "/",title = "Select segmentation file",filetypes = (("nii files","*.gz"),("all files","*.*")))
        if (completePath == ''):#cas ou on clique sur la croix de la fenetre et ou aucun chemin n'est rentre
            return
        else:
            try:
                (path, fileName) = os.path.split(completePath)
            except TypeError:
                pass
            else:
                self.home.model.createSegmentationMat(path, fileName)

                self.home.updateImagePanel()
        return

    def loadGraph(self):
        #ouvre une fenetre de dialogue pour ouvrir un fichier du bon format
        completePath = filedialog.askopenfilename(initialdir = "/",title = "Select graph file",filetypes = (("json files", "*.json"),("all files","*.*")))
        if (completePath == ''):#cas ou on clique sur la croix de la fenetre et ou aucun chemin n'est rentre
            return
        else:
            try:
                (path, fileName) = os.path.split(completePath)
            except TypeError:
                pass
            else:
                self.home.model.createGraph(path, fileName)

                self.home.updateImagePanel()
        return


    def remove3DImage(self): #lorsqu'on clique sur la croix : vide les chaines de charactere et update
        self.home.model.fileName = ''
        self.home.model.path = ''
        self.home.updateImagePanel()
        return

    def removeSegmentation(self): #lorsqu'on clique sur la croix : vide les chaines de charactere et update
        self.home.model.segFileName = ''
        self.home.model.segPath = ''
        self.home.updateImagePanel()
        return

    def removeGraph(self): #lorsqu'on clique sur la croix : vide les chaines de charactere et update
        self.home.model.graphFileName = ''
        self.home.model.graphPath = ''
        self.home.updateImagePanel()
        return


    def saveSegmentation(self): #lorsqu'on clique sur le bouton save, ouvre une fentre de dialogue pour sauvegarder
        toSave = self.home.model.checkIfSegToSave()
        if(toSave): #verifie s'il y a bien qqch a sauvegarder
            completePath = filedialog.asksaveasfilename(initialdir = "/",title = "Save your Segmentation file") + '.nii.gz' #, defaultextension='.nii.gz')
            try:
                (path, fileName) = os.path.split(completePath)
            except TypeError:
                pass
            else:
                self.home.model.saveSegToNifti(path, fileName) #fait la sauvegarde du fichier
                self.home.imagePanel.titleSegmentation['text'] = 'Segmentation : Generated [saved]'
                self.home.imagePanel.titleSegmentation.grid()

        else:
            if self.home.model.segPath=='': #cas il n'y a pas de fichier chargé
                self.home.popup.warning('No file found', 'There is currently no generated segmentation file to save.')
            else:
                self.home.popup.info('Nothing to save', 'The displayed segmentation file is already saved. You can only save generated segmentation files.')
        return

    def saveGraph(self): #lorsqu'on clique sur le bouton save, ouvre une fentre de dialogue pour sauvegarder
        toSave = self.home.model.checkIfRAGToSave()
        if(toSave): #verifie s'il y a bien qqch a sauvegarder
            completePath = filedialog.asksaveasfilename(initialdir = "/",title = "Save your Segmentation file", defaultextension='.json')
            try:
                (path, fileName) = os.path.split(completePath)
            except TypeError:
                pass
            else:
                self.home.model.saveRAGToJson(path, fileName) #fait la sauvegarde du fichier
                self.home.imagePanel.titleGraph['text'] = 'Graph : Generated [saved]'
                self.home.imagePanel.titleGraph.grid()

        else:
            if self.home.model.graphPath=='': #cas il n'y a pas de fichier chargé
                self.home.popup.warning('No file found', 'There is currently no generated graph file to save.')
            else:
                self.home.popup.info('Nothing to save', 'The displayed graph file is already saved. You can only save generated graph files.')
        return




class LayerButtons:

    commandFrame = None
    layerOptionsFrame = None #frame contenant les boutons avec les options de layers
    sliderAlpha = None #slider pour la transparence de la segmentation
    home = None
    buttons = [] #liste des boutons de ce frame

    def __init__(self, master, home):
        self.commandFrame = master
        self.home = home
        return

    def showLayerOptions(self, b): #prend en parametre le bouton "Layer Options", ce qui permet de savoir s'il est enfonce ou non, et donc s'il faut afficher ou non les options de layers
        self.buttonState = b
        self.buttons = []

        #if (self.buttonState['relief']==RAISED):
        if (True): #macOS version
            self.buttonState.config(relief=SUNKEN)

            self.layerOptionsFrame = Frame(self.commandFrame, bg=ConstantFiles.lightGrey)
            self.layerOptionsFrame.pack(side = BOTTOM, pady=10)

            #creation des boutons
            b0 = ButtonPlus(self.layerOptionsFrame, text="0", image = ConstantFiles.icoStandard , command=(lambda :self.displayImage(b0))) #pour enlever la segmentation
            b0.colors()
            b0.grid(row=0,column=0, sticky=W)
            self.buttons.append(b0)

            b1 = ButtonPlus(self.layerOptionsFrame, text="1", image = ConstantFiles.icoSegmentation, command=(lambda :self.displaySegmentation(b1))) #pour montrer la couleur
            b1.colors()
            b1.grid(row=0,column=1, sticky=W, padx=10)
            self.buttons.append(b1)

            b2 = ButtonPlus(self.layerOptionsFrame, text="2", image = ConstantFiles.icoGraph, command=(lambda :self.displayGraph(b2))) #pour affciher le graphe
            b2.colors()
            b2.grid(row=0,column=2, sticky=W)
            self.buttons.append(b2)

            # b3 = ... Il est possible d'en rajouter tres facilement car on y accede par une liste

            self.buttonManagement() #voir la fonction suivante

        elif (self.buttonState['relief']==SUNKEN):
            self.buttonState.config(relief=RAISED)
            self.layerOptionsFrame.destroy()

        b.colors()

    def buttonManagement(self):  #sert a savoir si les boutons de segmentation doivent etre enfonces ou pas, puis a les enfoncer si besoin
        for button in self.buttons:
            id = int(button['text'])
            if (self.home.model.layerSet[id]): #layerSet[id] == True si bouton enfonce
                button.config(relief=SUNKEN)
            else:
                button.config(relief=RAISED)
            button.colors()


    def displayImage(self, button): #affiche le background (3D Medical Image)
        layerId = int(button['text'])
        self.home.model.buttonActionLayer(layerId)
        self.buttonManagement()
        return

    def displaySegmentation(self, button): #affiche la segmentation et le curseur alpha
        layerId = int(button['text'])
        self.home.model.buttonActionLayer(layerId)
        self.buttonManagement()

        if (self.home.model.layerSet[1]==True): #si c'est la segmentation, afficher le curseur alpha
            self.sliderAlphaLabel = Label(self.home.imagePanel.imageFrame, text='Alpha Transparency Slider', font = "Helvetica 10", bg=ConstantFiles.darkGrey, fg='white')
            self.sliderAlphaLabel.pack()
            self.sliderAlpha = Scale(self.home.imagePanel.imageFrame,  from_=0, to=1, resolution=0.01, length = ConstantFiles.sliderSize, orient=HORIZONTAL, bg=ConstantFiles.darkGrey, fg='white', troughcolor=ConstantFiles.middleGrey, highlightthickness=0, command=self.home.model.setAlpha)
            self.sliderAlpha.set(self.home.model.alpha) #regle la valeur initiale du slider
            self.sliderAlpha.pack()
        else : #enleve l'affichage du slider
            self.sliderAlphaLabel.destroy()
            self.sliderAlpha.destroy()

        return

    def displayGraph(self, button): #affiche le graphe
        layerId = int(button['text'])
        self.home.model.buttonActionLayer(layerId)
        self.buttonManagement()
        return


class ButtonPlus(Button): #classe qui ajoute une methode a un Button classique

    def colors(self): #cette methode accorde les couleurs des boutons du CommandPanel avec les couleurs constantes choisies
        if (self['relief']==SUNKEN):
            self.config(bg = ConstantFiles.buttonSunken)
        elif (self['relief']==RAISED):
            self.config(bg = ConstantFiles.buttonRaised)


class Popup: #classe qui facilite la creation de popup/messagebox

    def __init__(self, home):
        home.model.listeners['popup'] = self
        return

    def info(self, title, content):
        messagebox.showinfo(title, content)

    def warning(self, title, content):
        messagebox.showwarning(title, content)



class ConstantFiles: #classe qui contient toutes les constantes
    #les constantes numeriques sont donnees directement, les autres son calculees par l'initialisation des variables de classes avec start

    #tailles d'icones
    iconSize = 40
    iconSizeMedium = 30
    iconSizeSmall = 20

    #logos de la fenetre
    logoWindows = 'icons_flat/logo.ico'
    logoLinux = '@icons_flat/logo.xbm'

    #icone des layers options
    icoStandard = None
    icoSegmentation = None
    icoGraph = None

    #icones du image Panel
    icoSizeRefresh = None
    icoRotate = None
    icoHelp = None

    #icones de sauvegarde et de suppression
    icoCross = None
    icoSave = None

    #couleurs
    lightGrey = 'grey80'
    middleGrey = 'grey30'
    darkGrey = 'black'

    buttonRaised = 'grey95'
    buttonSunken = 'grey65'

    #autres tailles fixes
    sliderSize = 270
    zoomFactor = 3 #facteur de multiplication du zoom

    def start(cls) : #initialisations
        cls.icoStandard = ImageTk.PhotoImage(Image.open('icons_flat/standard.png').resize((cls.iconSize, cls.iconSize), Image.LANCZOS))
        cls.icoSegmentation = ImageTk.PhotoImage(Image.open('icons_flat/segmentation.png').resize((cls.iconSize, cls.iconSize), Image.LANCZOS))
        cls.icoGraph = ImageTk.PhotoImage(Image.open('icons_flat/graph.png').resize((cls.iconSize, cls.iconSize), Image.LANCZOS))

        cls.icoSizeRefresh = ImageTk.PhotoImage(Image.open('icons_flat/sizeRefresh.png').resize((43, 24), Image.LANCZOS))
        cls.icoRotate = ImageTk.PhotoImage(Image.open('icons_flat/rotate.png').resize((43, 24), Image.LANCZOS))

        cls.icoCross = ImageTk.PhotoImage(Image.open('icons_flat/cross.png').resize((cls.iconSizeSmall, cls.iconSizeSmall), Image.LANCZOS))
        cls.icoSave = ImageTk.PhotoImage(Image.open('icons_flat/save.png').resize((cls.iconSizeSmall, cls.iconSizeSmall), Image.LANCZOS))

        cls.icoHelp = ImageTk.PhotoImage(Image.open('icons_flat/help.png').resize((cls.iconSizeMedium, cls.iconSizeMedium), Image.LANCZOS))

    start = classmethod(start)