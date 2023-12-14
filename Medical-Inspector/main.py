from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from PIL import Image, ImageTk

import model
import controller
import view

#creation de la window
window = Tk()
window.title('Medical Inspector 3D V3.0.4')
window.geometry("720x640")
window.minsize(720,640)

def center(win): #Afin d'afficher la windows de l'application au centre de l'écran de l'utilisateur
    win.update_idletasks()
    width = win.winfo_width()
    height = win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry('{}x{}+{}+{}'.format(width, height, x, y))

center(window)

window.configure(bg='black')
window.update()

if (os.name=='nt'): #Pour afficher une icone
    window.iconbitmap(view.ConstantFiles.logoWindows)
else:
    window.iconbitmap(view.ConstantFiles.logoLinux)

#Création du model, de la view, le controller consiste en des méthodes statiques
model = model.Model()
view.View(window, model)

#Lancement de l'app
window.mainloop()
