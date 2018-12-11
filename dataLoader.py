# THIS SCRIPT HANDLES DATA PROCESSING
''' Requirements: H5 and Table
	keyname: img, label
'''
import tables
import glob

import os
import sys

#image io and processing
import cv2
import PIL
import numpy as np

#patch extraction and dataset split: Use 1 pair of train-validation to due to limitation of time
from sklearn import model_selection
import sklearn.feature_extraction.image
from sklearn.feature_extraction.image import extract_patches
import random

from tqdm import tqdm
from types import SimpleNamespace


class dataLoader():


	''' The constructor of the class. Some of the logic are inspired from the blog and its corresponding code here:
			http://www.andrewjanowczyk.com/pytorch-unet-for-digital-pathology-segmentation/
		Args:
			Mandatory:
				filedir: base dir of the image
				pattern: wildcard pattern of the images. Default is *.jpg
				database_name: file name of the database
				export_dir: location to write the table
				patch_shape: Tuple. shape of the patch. Either (size,size,channel) or (size,size) in case of 1-channel images.
				stride_size: overlapping of patches.
			Optional:
				interp: the interpolation method, default is PIL.IMAGE.BICUBIC
				resize: the factor of resize the processing, which is 1/downsample_factor.
				dtype:  data type to be stored in the pytable. Default: UInt8Atom
				test_ratio: ratio of the dataset as test. Default: 0.1
		Raises:
			KeyError if the mandatory inputs is missing
	'''
	def __init__(self,**kwargs):
		self.filedir = kwargs['filedir']
		self.pattern = kwargs['pattern']
		self.database_name = kwargs['database_name']
		self.export_dir = kwargs['export_dir']


		self.patch_size = kwargs['patch_size']
		self.stride_size = kwargs['stride_size']

		self.interp = kwargs.get('interp',PIL.Image.BICUBIC)
		self.resize = kwargs.get('resize',0.5)
		self.dtype =  kwargs.get('dtype',tables.UInt8Atom())
		self.test_ratio = kwargs.get('test_ratio',0.1)

		self.filenameAtom = tables.StringAtom(itemsize=255)

		self.filelist = self.get_filelist()
		#for now just take 1 set of train-val shuffle. Leave the n_splits here for future use.
		self.phases = self.init_split()

	def get_filelist(self,filedir,pattern):
		file_pattern = os.path.join(filedir,pattern)
		files=glob.glob(file_pattern)
		return files

	def init_split(self):
		phases = {}
		phases['train'],phases['val'] = next(iter(model_selection.ShuffleSplit(n_splits=10,test_size=self.test_ratio).split(self.filelist)))
		return phases

	def generate_pair(self,file):
		img = cv2.imread(file,cv2.COLOR_BGR2RGB)
		img_down = cv2.resize(img,(0,0),fx=resize,fy=resize, interpolation=self.interp)
		img_down = cv2.resize(img_down,img.shape[0:2],interpolation=self.interp)
		return img,img_down

	def generate_patch(image):
		patches_label= extract_patches(image,self.patch_shape,self.stride_size)
		patches_label = .reshape((-1,)+self.patch_shape)
		return

	# Tutorial from  https://github.com/jvanvugt/pytorch-unet
	def execute(self):
		h5arrays = {}
		debug = {}
		filters=tables.Filters(complevel= 5)
		types = ['img','label']
		#for each phase create a pytable
		for phase in self.phases.keys():
			#export dir  -- use normal formatted string so it can be run on python3.6
			pytable_dir = os.path.join(self.export_dir,"%s_%s.%s" %(self.dataname,phase,'.pytable'))
			pytable = tables.open_file(pytable_dir, mode='w')
			debug[phase] = pytable


			for type in types:
				h5arrays[type]= pytable.create_earray(pytable.root, type, self.dtype,
													  shape=np.append([0],self.patch_shape),
													  chunkshape=np.append([1],self.patch_shape),
													  filters=filters)

			#
			#cv2.COLOR_BGR2RGB
			for file_id in tqdm(phases[phase]):
				#img as label,
				file = self.filelist[file_id]
				h5arrays['filename'] = pytable.create_earray(pytable.root, 'filename', self.filenameAtom, (0,))
				img_truth,img_down = self.generate_pair(file)

				patches = {}
				patches[types[0]] = self.generate_patch(img_truth)
				patches[types[1]] = self.generate_patch(img_down)
				for type in types:
					h5arrays[type].append(patches[type])

			h5arrays["filename"].append([file for x in range(patches[0].shape[0])])
			for k,v in h5arrays.items:
				v.close()
