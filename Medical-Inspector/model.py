from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
import json
import networkx as nx
from skimage import draw
from PIL import Image, ImageTk

import controller

class Model :
    #Un dictionnaire qui contient l'ensemble des listeners i.e. quand l'objet est créé dans la view il se référence au près du model
    #en s'ajoutant dans ce dictionnaire
    listeners = dict()

    #Valeur par défaut pour avoir des données pré-chargées au démarrage de l'app
    fileName = '1.nii.gz' #Pour l'IRM
    path = 'images'
    segFileName = 'labelmap1.nii.gz' #Pour la segmentation
    segPath = 'images'
    graphFileName = 'graph1.json' #Pour le graph (JSon)
    graphPath = 'images'

    #Pour l'overlay :
    sliderValue = 0 #La valeur du slicer, i.e. quel z on regarde
    alpha = 0.5 #La part de transparence de du layer1 (= segmentation) qu'on va rajouter sur le layer0 (= l'IRM)

    bgMat = None #La matrice 3D de l'irm issu du Nifti
    windowLBgMat = None #La matrice 3D de l'irm après window level
    shape = None #Les dimensions des données chargées
    maxZ = 0 #L'indice z max donc shape[2] - 1
    shapeLeaders = [False, False, False] #Liste les layers (0 = IRM, 1 = segmentation, 2 = graph) qui sont chargés (ouvert depuis un fichier ou généré)
    spacing = None #La taille des voxels issu de l'header du Nifti
    affine = None #L'orientation du Nifti

    segmentation = None #La matrice 3D de la segmentation, chaque région repéré par un label entier
    coloredSegmentation = None #La matrice 3D de la segmentation une fois colorisé grâce à une colorMap

    graphMat = None #La matrice 3D du graph dessiné
    rag = None #Le rag du graph (format graph de networkX)

    displayedImg = None #L'image qu'on affiche dans la view, issu du calcul des layers
    windowW = None #La valeur de la window, la largeur
    windowL = None #La valeur du window level
    windowLMin = None #La valeur min de bgMat
    windowLMax = None #La valeur max de bgMat

    #Indique quel layer sont a afficher i.e. quel bouton du layer option sont enfoncés
    layerSet = [False, False, False] #0 pour background, 1 pour la segmentation et 2 pour le graph

    def __init__(self) :
        return

##Pour l'imagePanel
    def setFileName(self, path, fileName) :
        self.path = path
        self.fileName = fileName

    def setSegFileName(self, path, fileName) :
        self.segPath = path
        self.segFileName = fileName
    
    def setGraphFileName(self, path, fileName) :
        self.graphPath = path
        self.graphFileName = fileName

    #Retourne la matrice 3D correspondant à un nifti indiqué par path et fileName
    def createMatNifti(self, path, fileName, updateNiftiData):  #Ajouter un try catch ??
        if(path=='' or fileName==''): #toujours utlie ? car teste deja fait aussi dans createBgMat et les autres ...
            Mat = None

        else:
            image = os.path.join(path, fileName)
            load = nib.load(image)
            Mat = load.get_fdata()
            if updateNiftiData : 
                self.spacing = self.getSpacingFromNifti(load)   
                self.affine = load.affine         
        return Mat

    #Retourne la taille d'un voxel a partir d'un nifti
    def getSpacingFromNifti(self, nifti) : #Ajouter cas ou header du nifti ne serait pas rempli...
        #return (nifti.header['pixdim'][1:4]/nifti.header['pixdim'][1]).astype(float)
        return nifti.header['pixdim'][1:4].astype(float) #on ne fait pas la division car l'équipe graph clustering avait fait ses tests d'optimisation sans cette division

    #Ajouter un layer parmis les shapeLeaders
    def setShapeLeaders(self, layer, shape) :
        self.shapeLeaders[layer] = True
        self.shape = shape
        self.maxZ = self.shape[2] - 1
    
    #Pour savoir si un layer peut imposer ses dimensions, le premier arrivé impose sa shape,
    #Pour charger un autre fichier il doit avoir les bonnes dimensions sinon il sera refusé
    def canTakeShapeLead(self, layer) :
        return (True not in self.shapeLeaders) or (self.shapeLeaders[layer] == True and self.shapeLeaders.count(True) == 1) #Pas de leader ou 1 seul leader et c'est lui meme

    #Une fois la donnée supprimé (croix rouge de la view), on load cette donné par un valeur par défaut (matrice de 0)
    #Arguement hasAlpha utilisé pour la valeur par défaut de graphMat qui a besoin d'un canal alpha
    def loadDefaultMat(self, hasAlpha) :
        if True not in self.shapeLeaders : #pas de leader
            self.shape = [1, 1, 1] if not hasAlpha else [1, 1, 1, 1]
            self.maxZ = 0 
            return np.zeros(self.shape)
        else : #il y a un leader donc charge une matrice vide de sa taille
            return np.zeros(self.shape) if not hasAlpha else np.zeros((self.shape[0], self.shape[1], self.shape[2], 4))
    
    #Méthode a éviter d'appeler directement, car elle ne réalise par tous les tests nécessaire
    #À utiliser de préférence que dans d'autre fonction,
    #Elle permet de mettre à jour automatiquement les données lié au bgMat, lorsqu'on laod un nouveau bgMat
    def setBgMat(self, mat) :
        self.bgMat = mat
        self.layerSet[0] = True
        self.windowLMin = np.min(self.bgMat)
        max = np.max(self.bgMat)
        self.windowLMax = max if max > 0 else 1
        #Calculer valeur par defaut de windowW et windowL pour calculer la windowLBgMat
        self.windowL = int((self.windowLMax - self.windowLMin) / 2)
        WW = int(self.windowLMax - self.windowLMin)
        self.windowW = WW if WW > 0 else 1
        self.generateWindowLBgMat(self.bgMat)
        self.drawLayers()
    
    #Load la bgMat à partir d'une matrice en verifiant si les dimensions sont bonnes
    #Reourne true si la matrice a bie été set
    def loadBgMat(self, mat) :
        if self.canTakeShapeLead(0) : #Alors impose sa shape
                self.setShapeLeaders(0, mat.shape) #A faire avant le setBgMat
                self.setBgMat(mat)
                return True
        else :
            #On verifie si bonne shape
            if (mat.shape == self.shape) :
                self.setShapeLeaders(0, mat.shape) #On ajoute aussi cette matrice parmis les leaders, car les données correspondant à ce layer vont être chargés par le set
                self.setBgMat(mat)
                return True
            else : #Prevenir la vue qu'on load une donnée qui n'a pas la bonne shape
                self.listeners['popup'].warning("Wrong shape", "Please load another file with the same shape as other current layers. The current shape is : " + str(self.shape) + ". If you want to use this layer, please delete the loaded layers before.")
                return False    

    #Load la bgMat à partir d'un fichier nifi indiqué par son chemin path + fileName
    def createBgMat(self, path, fileName):
        if (path != '') :
            mat = self.createMatNifti(path, fileName, True) #met aussi a jour le spacing
            if (self.loadBgMat(mat)) : #Si la bgMat est bien load on met à jour son path et fileName
                self.setFileName(path, fileName)
        else : #On arrive ici si utilisateurs appuient sur la croix rouge a cote de IRM, donc libere son eventuelle lead
            self.shapeLeaders[0] = False
            self.setBgMat(self.loadDefaultMat(False))
            self.setFileName('', '')
            self.removeLayer(0) #On a change les boutons donc notifie la view
            self.listeners['commandPanel'].layerOptionsFrame.buttonManagement()
    


    #Génère la coloredSegmentation a partir d'une segmentation
    #Utilise la valeur alpha que l'utilisateur sélecionne avec le slider alpha de la vue
    def segmentationToColoredSegmentation(self) :
        M=np.max(self.segmentation)
        m=np.min(self.segmentation)
        out =  ((255/(M - m) * (self.segmentation - m)).astype('uint8')) if M > 0 else np.copy(self.segmentation)

        alphaChanel = np.zeros(self.shape)
        alphaChanel[self.segmentation != 0] = self.alpha*255

        cmap = plt.get_cmap('gist_rainbow')
        coloredMat = cmap(out)*255
        coloredMat[:,:,:,3] = alphaChanel

        self.coloredSegmentation = coloredMat.astype('uint8')
    
    #Cf setBgMat
    def setSegmentationMat(self, mat) :
        self.segmentation = mat.astype(int)
        self.segmentationToColoredSegmentation() #Lorsqu'on charge une nouvelle segmentation il faut généré la coloredSegmentation
        self.drawLayers()
    
    #Cf loadBgMAt
    def loadSegmentationMat(self, mat) :
        if self.canTakeShapeLead(1) :
                self.setShapeLeaders(1, mat.shape)
                self.setSegmentationMat(mat)
                return True
        else :
            if (mat.shape == self.shape) :
                self.setShapeLeaders(1, mat.shape)
                self.setSegmentationMat(mat)
                return True
            else :
                self.listeners['popup'].warning("Wrong shape", "Please load another file with the same shape as other current layers. The current shape is : " + str(self.shape) + ". If you want to use this layer, please delete the loaded layers before.")
                return False

    #Cf createBgMat
    def createSegmentationMat(self, path, fileName) :
        if (path != '') : #Bien faire en deux if imbriqué car le premier if distingue No segmentation (apres croix) du reste, et le deuxieme distingue si on charge une segmentation precedemment genere ou si depuis fichier
            if (fileName != '') :
                mat = self.createMatNifti(path, fileName, False)
                if (self.loadSegmentationMat(mat)) :
                    self.setSegFileName(path, fileName)
        else :
            self.shapeLeaders[1] = False
            self.setSegmentationMat(self.loadDefaultMat(False))
            self.setSegFileName('', '')
            self.removeLayer(1) #On a change les boutons donc notifie la view
            self.listeners['commandPanel'].layerOptionsFrame.buttonManagement()
    
    #Utilisé par la vue pour savoir s'il y a bien une segmentation a sauvé lorsque l'utilisateur clique sur le bouton save de la vue
    def checkIfSegToSave(self) :
        return (self.segFileName == '') and (self.segPath == 'generated')
    
    #Pour sauver une segmentation en Nifti
    #Il faut avoir avant verifier si il y a bien une donnée à save avec checkIfSegToSave
    def saveSegToNifti(self, path, fileName): #file sous la forme "filename.nii.gz"
        if (path != '') :
            array_img = nib.Nifti1Image(self.segmentation, self.affine)
            nib.save(array_img, os.path.join(path, fileName))
            self.setSegFileName(path, fileName)



    #Load un raf à partir d'un fichier json
    #Il faut ensuite check si le rag obtenu a le bon format avec checkRagFormat
    def openRAGFromJson(self, path, fileName) : #Ajouter un try catch ??
        filePointer = open(os.path.join(path, fileName),"r")
        data = json.load(filePointer)
        g = nx.readwrite.json_graph.node_link_graph(data)
        filePointer.close()
        return g
    
    #Verifie si le rag contient bien toute l'information nécessaire
    def checkRagFormat(self, rag) :
        edge = list(rag.edges)[0]
        return (('shape' in rag.graph) and ('maxD' in rag.graph) and ('centroid' in rag.nodes[1]) and ('weight' in rag[edge[0]][edge[1]]) and ('similarity' in rag[edge[0]][edge[1]]) and ('euclideanDist' in rag[edge[0]][edge[1]]) and ('xDist' in rag[edge[0]][edge[1]]) and ('yDist' in rag[edge[0]][edge[1]]) and ('zDist' in rag[edge[0]][edge[1]]))

    #Pour le dessin du graph
    #La largeur d'une arête est fonction de la distance entre les deux voisins, plus ils sont similaires plus l'arête est large
    #d la distance entre les deux voisins
    #maxD la distance max entre deux voisins dans le rag
    #maxT la largeur max d'une arête
    def distanceToThickness(self, d, maxD, maxT) :
        return (maxT-1) * (np.exp(-d**2/maxD)) + 1
    
    #Pour le dessin du graph
    #Retourne les coins du rectangle qui corresond à un trait entre P1 et P2 avec une largeur thickness
    #P1 et P2 sont des coordonnées
    def thickLine(self, P1, P2, thickness) : #P1 et P2 les deux extrémité du segment    
        u = np.array([P2[0] - P1[0], P2[1] - P1[1]]) #Le vecteur directeur de la droite
        n = np.array([-u[1], u[0]])
        norm = np.linalg.norm(n)
        nN = n if norm == 0 else n / norm
        
        corners = np.zeros((4, 2))
        corners[0, :] = -thickness/2 * nN + P1
        corners[1, :] = thickness/2 * nN + P1
        corners[3, :] = -thickness/2 * nN + P2
        corners[2, :] = thickness/2 * nN + P2
        
        return corners.astype(int)
    
    #Pour le dessin du graph
    #Retourne la couleur de l'arête en fonction du delta Z entre les deux voisins :
    #Jaune voisin au dessus
    #Rouge voisin en dessous
    #Orane même niveau
    #dZ le delta Z entre les deux voisins influence la transparence de l'arête, plus ils sont éloignés plus elle est transparente
    #zMax la hauteur de la bgMat, correspond donc au plus grand dZ possible
    def deltaZToColor(self, dZ, zMax) :
        amax = 75 #La valeur max du alpha d'une arête, quand dZ = 0
        amin = 10 #La valeur min du alpha d'une arête, quand abs(dZ) = zMax
        
        a = (amin - amax/zMax) * np.abs(dZ) + amax
        alpha = np.array([0, 0, 0, 1])
        red = np.array([202, 0 ,0, 0])
        yellow = np.array([199, 182, 0, 0])
        if dZ > 0 :
            return yellow + a * alpha
        if dZ < 0 :
            return red + a * alpha
        return [255, 153 ,85, amax] #si dZ = 0 n revoie l'arête est orange

    #Génère le graphMat à partir du rag chargé, i.e. dessine le graph est sauve ce dessin du graph dans graphMat
    #Chaque sommet sont dessinés au coordonné du centroid de la region de la segmentation à laquelle il correspond
    #Les arêtes sont dessiné comme indiqué precédemment (distanceToThickness et deltaZToColor)
    def ragToGraphMat(self, maxT) : #A appeler qu'une fois que la rag a été validé, on utilise donc la valeur des attributs              
        zMax = self.shape[2]
        maxD = self.rag.graph['maxD']
              
        self.graphMat = np.zeros((self.shape[0], self.shape[1], zMax, 4)).astype(np.uint8)
        
        for z in range(zMax) :
            for n in self.rag :
                x0, y0, z0 = self.rag.nodes[n]['centroid']
                x0 = int(x0)
                y0 = int(y0)
                z0 = int(z0)
                
                if (int(z0) == z):          
                    for v in self.rag.neighbors(n) :
                        d = self.rag[n][v]['weight']
                        corners = self.thickLine((x0 , y0), (int(self.rag.nodes[v]['centroid'][0]), int(self.rag.nodes[v]['centroid'][1])), self.distanceToThickness(d, maxD, maxT))
                        rTL, cTL = draw.polygon(corners[:, 0], corners[:, 1], self.shape[0 : 2])
                        self.graphMat[rTL, cTL, z,:] = self.deltaZToColor(int(self.rag.nodes[v]['centroid'][2]) - z0, zMax)
            
            #On dessine ENSUITE les sommets pour les avoir au dessus des aretes
            for n in self.rag :
                x0, y0, z0 = self.rag.nodes[n]['centroid']
                x0 = int(x0)
                y0 = int(y0)
                z0 = int(z0)
                if (int(z0) == z):
                    rC, cC = draw.disk((x0, y0), 5, shape = self.shape[0 : 2])
                    #On met ces pixels à une valeur différente de 0
                    self.graphMat[rC, cC, z,:] = [0, 204 , 255, 120]
    
    #Cf setBgMAt
    #L'argument default permet de chargé un rag par défaut
    def setGraph(self, rag, default) :
        if not default :
            self.rag = rag
            self.ragToGraphMat(3)
        else :
            self.rag = rag
            self.graphMat = self.loadDefaultMat(True)
        self.drawLayers()
    
    #Cf loadBgMat
    #Si on veut juste load un rag sans le dessiner mettre noMAT à true, utilise lors du generate graph de la vue
    #Si on ne le dessine pas alors charge graphMat avec sa valeur par défault
    def loadGraph(self, rag, noMat) :
        if (self.checkRagFormat(rag)) :
            if self.canTakeShapeLead(2) :
                self.setShapeLeaders(2, tuple(rag.graph['shape']))
                self.setGraph(rag, noMat)
                return True
            else :
                if (tuple(rag.graph['shape']) == self.shape) :
                    self.setShapeLeaders(2, tuple(rag.graph['shape']))
                    self.setGraph(rag, noMat)
                    return True
                else : #Si pas même dimension
                    #Prevenir la view
                    self.listeners['popup'].warning("Wrong shape", "Please load another file with the same shape as other current layers. The current shape is : " + str(self.shape) + ". If you want to use this layer, please delete the loaded layers before.")
                    return False
        else : #Si le json n'était pas du bon format
            self.listeners['popup'].warning("Wrong graph format", "The graph has not the right format")
            return False

    #Cf createBgMat
    def createGraph(self, path, fileName) :
        if (path != '') :
            if (fileName != '') :
                rag = self.openRAGFromJson(path, fileName)
                if (self.loadGraph(rag, False)) :
                    self.setGraphFileName(path, fileName)
        else :
            self.shapeLeaders[2] = False
            self.setGraph(None, True)
            self.setGraphFileName('', '')
            self.removeLayer(2) #On a change les boutons donc notifie la view
            self.listeners['commandPanel'].layerOptionsFrame.buttonManagement()

    #Cf checkIfSegToSave
    def checkIfRAGToSave(self) :
        return (self.graphFileName == '') and (self.graphPath == 'generated')
    
    #Cf saveSegToNifti
    def saveRAGToJson(self, path, fileName) :
        class NpEncoder(json.JSONEncoder): #Merci à Jie Yang du forum stackoverflow
            def default(self, obj) :
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                else:
                    return super(NpEncoder, self).default(obj)

        if (path != '') :
            data = nx.readwrite.json_graph.node_link_data(self.rag)
            filePointer = open(os.path.join(path, fileName),"w")
            json.dump(data, filePointer, indent=2, cls = NpEncoder)
            filePointer.close()
            self.setGraphFileName(path, fileName)




##Pour le dessin des layers
    #Génère la window level irm à partir d'une irm
    #Attention windowW >= 1, sinon division par 0
    #Le slider de W dans la vue permet d'avoir un W >= 1s
    def generateWindowLBgMat(self, mat) : #Prend une matrice 3D en entrée
        P1 = self.windowL - self.windowW/2
        P2 = self.windowL + self.windowW/2
        self.windowLBgMat =  np.clip((255/(P2 - P1) * (mat - P1)), 0, 255).astype('uint8')

    #Génère la displayImg en fonction des layers séléctionnés
    def drawLayers(self) :
        self.displayedImg = Image.fromarray(np.zeros(self.shape[0 : 2])).convert('RGB')

        if self.layerSet[0] : #Calculer avec W et L
            self.displayedImg = Image.fromarray(self.windowLBgMat[ : , : , self.sliderValue]).convert('RGB')
        if self.layerSet[1] :
            img1 = Image.fromarray(self.coloredSegmentation[ : , : , self.sliderValue, :], 'RGBA') #mettre dans la bonne slice
            self.displayedImg.paste(img1, (0, 0), img1)
        if self.layerSet[2] :
            img2 = Image.fromarray(self.graphMat[ : , : , self.sliderValue, :], 'RGBA')
            self.displayedImg.paste(img2, (0, 0), img2)

        #On notifie la vue que la displayImg a été changée pour qu'il refresh le canva
        self.listeners['imagePanel'].displayImage()

    #Ajouter un layer a afficher
    def addLayer(self, layer) :
        if (layer == 0) : #Irm
            self.layerSet[0] = True
            self.drawLayers()

        elif (layer == 1) : #Segmentation
            self.layerSet[1] = True
            self.drawLayers()

        elif (layer == 2) : #Graph
            self.layerSet[2] = True
            self.drawLayers()
    
    #Retirer un layer a afficher
    def removeLayer(self, layer) :
        if (layer == 0) :
            self.layerSet[0] = False
            self.drawLayers()
        
        elif (layer == 1) :
            self.layerSet[1] = False
            self.drawLayers()

        elif (layer == 2) :
            self.layerSet[2] = False
            self.drawLayers()



    ##Fonctions pour certain bouton de la vue
    #Bouton du layer option
    def buttonActionLayer(self, layer) :
        if self.layerSet[layer] :
            self.removeLayer(layer)
        else :
            self.addLayer(layer)
    
    #Pour le slider Z
    def setSliderValue(self, value) :
        self.sliderValue = int(value)
        self.drawLayers()

    #Pour le slider alpha
    def setAlpha(self, value) :
        self.alpha = float(value)
        self.segmentationToColoredSegmentation()
        self.drawLayers()
    
    #Pour le slider window L 
    def setWindowL(self, value) :
        self.windowL = int(value)
        self.generateWindowLBgMat(self.bgMat)
        self.drawLayers()
    
    #Pour le slider windowW
    def setWindowW(self, value) :
        self.windowW = int(value)
        self.generateWindowLBgMat(self.bgMat)
        self.drawLayers()




##Plugins function : Pour savoir si segmentation chargé shapeLeaderS[i]
    #Pour le plugin generate segmentation    
    def segmentationPlugin(self, optionNumber, values) :
        #Convetion
        # 0 : slic3D
        # 1 : watershedGradient3D
        # 2 : watershedMinima3D
        # 3 : waterVoxel3D
        if (self.shapeLeaders[0]) : #IRM chargé
            if optionNumber == 0 :
                self.listeners['Generate Segmentation'].success()
                if (self.loadSegmentationMat(controller.Segmentation.SLIC3D(self.bgMat, int(values[0]), values[1], self.spacing))) :
                    self.setSegFileName('generated', '')
                    self.listeners['imagePanel'].home.updateImagePanel()
            elif optionNumber == 1 :
                self.listeners['Generate Segmentation'].success()
                if (self.loadSegmentationMat(controller.Segmentation.watershedGradient3D(self.bgMat, int(values[0]), int(values[1]), int(values[2])))) :
                    self.setSegFileName('generated', '')
                    self.listeners['imagePanel'].home.updateImagePanel()
            elif optionNumber == 2 :
                self.listeners['Generate Segmentation'].success()
                if (self.loadSegmentationMat(controller.Segmentation.watershedMinima3D(self.bgMat, int(values[0]), values[1]))) :
                    self.setSegFileName('generated', '')
                    self.listeners['imagePanel'].home.updateImagePanel()
            else :
                if (0 < values[0] < 1) :
                    self.listeners['Generate Segmentation'].success()
                    if (self.loadSegmentationMat(controller.Segmentation.watervoxel3D(self.bgMat, values[0], int(values[1]), int(values[2]), int(values[3]), int(values[4]), values[5]))) :
                        self.setSegFileName('generated', '')
                        self.listeners['imagePanel'].home.updateImagePanel()
                else :
                    self.listeners['Generate Segmentation'].failure('The parameter a must belong to ]0, 1[.', False)
        else : #prevenir la vue pas d'irm chargé ou failure de plugin ?
            self.listeners['Generate Segmentation'].failure("No IRM loaded, please load an IRM first.", True)
            
    #Pour le plugin generate graph
    def graphGenerationPlugin(self, optionNumber, values) :
        #Convention
        # 0 : meanColor
        # 1 : boundary
        if (self.shapeLeaders[0] and self.shapeLeaders[1]) : #IRM et segmentation chargés
            if optionNumber == 0 :
                self.listeners['Generate Graph'].success()
                if (self.loadGraph(controller.GraphGeneration.meanColorRAG(self.bgMat, self.segmentation, values[0]), (int(values[1]) == 0))) :
                    self.setGraphFileName('generated', '')
                    self.listeners['imagePanel'].home.updateImagePanel()
            elif optionNumber == 1 :
                self.listeners['Generate Graph'].success()
                if (self.loadGraph(controller.GraphGeneration.boundaryRAG(self.bgMat, self.segmentation, values[0]), (int(values[1]) == 0))) :
                    self.setGraphFileName('generated', '')
                    self.listeners['imagePanel'].home.updateImagePanel()
        else :
            self.listeners['Generate Graph'].failure("No IRM or segmentation loaded, please load both first.", True)
    
    #Pour le plugin generate cluster
    def graphClusteringPlugin(self, optionNumber, values) :
        #Convetion
        # 0 : louvain
        # 1 : spectralClustering
        if (self.shapeLeaders[0] and self.shapeLeaders[1] and self.shapeLeaders[2]) : #IRM, segmentation et graph chargés
            if optionNumber == 0 :
                self.listeners['Generate Clusters'].success()
                if (self.loadSegmentationMat(controller.GraphClustering.louvain(self.rag, self.segmentation))) :
                    self.setSegFileName('generated', '')
                    self.listeners['imagePanel'].home.updateImagePanel()
            elif optionNumber == 1 :
                self.listeners['Generate Clusters'].success()
                if (self.loadSegmentationMat(controller.GraphClustering.spectralClustering(self.rag, self.segmentation, int(values[0])))) :
                    self.setSegFileName('generated', '')
                    self.listeners['imagePanel'].home.updateImagePanel()
        else :
            self.listeners['Generate Clusters'].failure("No IRM or segmentation or graph loaded, please load the three first.", True)