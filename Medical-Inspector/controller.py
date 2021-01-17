#Composer que de classe static
import numpy as np
import nibabel as nib
from scipy import ndimage as ndi
from skimage.segmentation import watershed, slic
from skimage.feature import peak_local_max
from skimage.future import graph
from skimage.measure import regionprops
from skimage.filters import sobel
from sknetwork.clustering import Louvain
from sklearn.cluster import SpectralClustering
import networkx as nx
import json
import cv2 as cv



class Segmentation : #Normalements la numerotation des segments commence à 1
    def SLIC3D(cls, data, n_segments, sigma, spacing) :
        #(x,y,z)=np.shape(data)
        #array_data = np.zeros((x, y, z), dtype=np.int8)
        data = SharedFunctions.scale(data)
        segments_slic = slic(data, n_segments=n_segments, compactness=0.05, sigma=sigma, start_label=1, spacing=spacing, multichannel=False)
        #array_data = scaleBis(segments_slic)
        return segments_slic

    SLIC3D = classmethod(SLIC3D)

    def watershedGradient3D(cls, data, gradient_threshold, gradient_size, footprint_median):
        #(x,y,z)=np.shape(data)
        #array_data = np.zeros((x, y, z), dtype=np.int8)
        data = SharedFunctions.scale(data)
        data = ndi.median_filter(data, footprint=np.ones((footprint_median,footprint_median,footprint_median)))
        gradient = ndi.morphological_gradient(data, size = (gradient_size,gradient_size,gradient_size))
        #c = np.shape(gradient)
        markers = SharedFunctions.threshold(gradient,gradient_threshold)
        markers = ndi.label(markers)[0]
        labels = watershed(gradient, markers)
        #array_data = labels
        #print(np.min(labels))
        return labels if np.min(labels) == 1 else labels + 1

    watershedGradient3D = classmethod(watershedGradient3D)

    def watershedMinima3D(cls, data, footprint_gaussian, sigma):
        #(x,y,z) = np.shape(data)
        #array_data = np.zeros((x, y, z), dtype=np.int8)
        data = SharedFunctions.scale(data)
        imf = ndi.gaussian_filter(data, sigma = sigma)
        distance = ndi.distance_transform_edt(imf)
        local_maxi = peak_local_max(distance, indices=False,footprint=np.ones((footprint_gaussian, footprint_gaussian, footprint_gaussian)), labels=imf)
        markers = ndi.label(local_maxi)[0]
        labels = watershed(-distance, markers, mask=imf, compactness=0.001)
        #array_data = labels
        #print(np.min(labels))
        return labels if np.min(labels) == 1 else labels + 1
    
    watershedMinima3D = classmethod(watershedMinima3D)

    def watervoxel3D(cls, data, a, gradient_threshold, gradient_size, footprint_median, footprint_gaussian, sigma):
        #(x,y,z)=np.shape(data)

        #array_data = np.zeros((x, y, z), dtype=np.int8)

        data = SharedFunctions.scale(data)

        #*****gradient*****#
        data1 = ndi.median_filter(data, footprint=np.ones((footprint_median,footprint_median,footprint_median)))

        gradient = ndi.morphological_gradient(data1, size = (gradient_size,gradient_size,gradient_size))
        #c=np.shape(gradient)

        markers1 = SharedFunctions.threshold(gradient,gradient_threshold)

        markers1 = ndi.label(markers1)[0]

        #******minima*******#
        imf = ndi.gaussian_filter(data, sigma = sigma)
        distance = ndi.distance_transform_edt(imf)
        local_maxi = peak_local_max(distance, indices=False,footprint=np.ones((footprint_gaussian, footprint_gaussian, footprint_gaussian)), labels=imf)
        markers2 = ndi.label(local_maxi)[0]

        #******both******#
        markers = (a*markers1 + (1-a)*markers2)
        tmp = (a*gradient - (1-a)*distance )
        labels = watershed(tmp, markers, compactness=0.001)

        #array_data = labels
        #print(np.min(labels))
        return labels if np.min(labels) == 1 else labels + 1
    
    watervoxel3D = classmethod(watervoxel3D)



class GraphGeneration :
    def meanColorRAG(cls, data, labels, sigma) :
        mat = np.copy(labels) + 1 if np.min(labels) == 0 else np.copy(labels)
        g = graph.rag_mean_color(data, mat, connectivity = 2)
        props = regionprops(mat)
        labelsToIndex = cls.labelsToPropsIndex(props)        
        cls.addData(g, data.shape, sigma,props, labelsToIndex)
        return g
    
    meanColorRAG = classmethod(meanColorRAG)

    def boundaryRAG(cls, data, labels, sigma) :
        edges = sobel(data)
        mat = np.copy(labels) + 1 if np.min(labels) == 0 else np.copy(labels)
        g = graph.rag_boundary(mat, edges, connectivity = 2)
        props = regionprops(mat)
        labelsToIndex = cls.labelsToPropsIndex(props)
        cls.addData(g, data.shape, sigma,props, labelsToIndex) 
        return g

    boundaryRAG = classmethod(boundaryRAG)

    def labelsToPropsIndex(cls, props) :
        labelsToIndex = []
        for i in range(len(props)) :
            labelsToIndex.append(props[i].label)
        return labelsToIndex

    labelsToPropsIndex = classmethod(labelsToPropsIndex)

    def addData(cls, g, shape, sigma, props, labelsToIndex) :
        g.graph['shape'] = shape
        
        max=0
        for (u, v) in g.edges():
            s1 = labelsToIndex.index(u)
            s2 = labelsToIndex.index(v)

            a, b, c = props[s1].centroid
            a2, b2, c2 = props[s2].centroid

            d1 = ((a-a2)**2 + (b-b2)**2 + (c-c2)**2)**(1/3)
            g.add_edge(u, v, euclideanDist = d1)

            d2 = abs(a-a2)
            g.add_edge(u, v, xDist = d2)

            d3 = abs(b-b2)
            g.add_edge(u, v, yDist = d3)

            d4 = abs(c-c2)
            g.add_edge(u, v, zDist = d4)

            d5 = g[u][v]['weight']

            if d5 > max:
                max = d5

            s = np.exp(-d5**2/sigma)
            g.add_edge(u, v, similarity = s)
        
        g.graph['maxD'] = max 

        for n in g:
            i = labelsToIndex.index(n)
            g.add_node(n, centroid=props[i].centroid)
    
    addData = classmethod(addData)

    

class GraphClustering :
    def ragToAdjacencyMatrix(cls, g, distance): #écrire sous la forme 'weight' distance
        n = g.number_of_nodes()
        mat = np.zeros([n,n])
        for (s1, s2) in g.edges():
            val=g[s1][s2][distance]
            mat[s1-1,s2-1]=val
            mat[s2-1,s1-1]=val
        return mat
    
    ragToAdjacencyMatrix = classmethod(ragToAdjacencyMatrix)

    def louvain(cls, g, labels):
        x, y, z=labels.shape
        t = cls.ragToAdjacencyMatrix(g,'similarity')
        louvain = Louvain() 
        l = louvain.fit_transform(t)
        rep = labels.copy()
        for k in range(x):
            for j in range(y):
                for i in range(z):
                    rep[k,j,i]=l[labels[k,j,i]-1]
        return rep
    
    louvain = classmethod(louvain)

    def spectralClustering(cls, g, labels, n):
        x,y,z=labels.shape
        clustering = SpectralClustering(n_clusters=n,assign_labels="discretize",random_state=0,affinity='precomputed').fit(cls.ragToAdjacencyMatrix(g,'similarity'))
        l = clustering.labels_
        rep=labels.copy()
        for k in range(x):
            for j in range(y):
                for i in range(z):
                    rep[k,j,i]=l[labels[k,j,i]-1]
        return rep
    
    spectralClustering = classmethod(spectralClustering)



class SharedFunctions() :
    def scale(cls, im):
        M=np.max(im)
        m=np.min(im)
        out =  ((255/(M - m) * (im - m)).astype('uint8'))
        return out

    scale = classmethod(scale)

    def threshold(cls, mat, gradient_threshold):
        ret,thresh = cv.threshold(mat,gradient_threshold,255,cv.THRESH_BINARY_INV)
        return thresh
    
    threshold = classmethod(threshold)