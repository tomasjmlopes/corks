# camera_controllers.py

"""
Description: This script is used to control the cameras in the experiment.
Author: Tiago D. Ferreira, Nuno A. Silva
Date Created: 23/02/2022
Python Version: 3.8.13
"""

import numpy as np
import time
import cv2
import ctypes

# TODO add the doctrings to all the methods and classes
# TODO correct all the types in the methods
# FIXME add the missiing methods on all the camera objects just for clarity


class CameraController():

    def __init__(self, camera_name, camera_index=0, thorcam_SDK=None):
        
        self.ready=False  #handle to know if the camera is armed
        
        if camera_name == 'Thorlabs':
            self.camera = ThorCam(camera_index, thorcam_SDK=thorcam_SDK)
            
        elif camera_name == 'OBS':
            self.camera = ObsCam()
            
        elif camera_name == "XIMEA":
            self.camera = XimeaCam() #THE MODULE THAT WE HAVE TO DEVELOP
            
        elif camera_name == "IDS":
            self.camera = IdsCam(camera_index)
            
                  
    #All the cameras have to have the following functions
    
    #Arm the camera
    def get_camera_ready(self):
        self.camera.get_camera_ready()
        self.ready=True
        
    #Get a frame or a the average of a number of frames (the number of frames is specified in the properties)
    def get_image(self) -> np.ndarray:
        return self.camera.get_image()
    
    #Set the camera properties. The propesties should be a dictionary
    def set_properties(self, properties):
        return self.camera.set_properties(properties)
    
    #Save the camera current properties
    def save_properties(self, folder_path):
        self.camera.save_properties(folder_path)
        
    def get_properties(self,ret=False):
        return self.camera.get_camera_properties(ret=ret)
    
    #Disarm the camera, but the camera object continues open
    def stop_camera(self):
        self.camera.stop_camera()
        self.ready=False
        
    #Closes the camera
    def close(self):
        return self.camera.close()
    
 
###############################################################################
#                                                                             #
#                            Thor cam                                         #
#                                                                             #
###############################################################################


class ThorCam():
    
    def __init__(self, camera_index=0, thorcam_SDK=None):

        if thorcam_SDK == None:
        
            try:
                # if on Windows, use the provided setup script to add the 
                #DLLs folder to the PATH
                from windows_setup import configure_path
                configure_path()
            except ImportError:
                configure_path = None

            from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, OPERATION_MODE

            self.sdk = TLCameraSDK()

        else:

            self.sdk = thorcam_SDK


        self.camera_index = camera_index
        
        
        available_cameras = self.sdk.discover_available_cameras()
        if len(available_cameras) < 1:
            print("No cameras detected")
        else:
            if camera_index == 0:
                self.camera = self.sdk.open_camera(available_cameras[0])
            else:
                if str(camera_index) in available_cameras:
                    self.camera = self.sdk.open_camera(str(camera_index))
                else:
                    print("Invalid index")
        
        self.num_frames = 1
        
        self.camera_initialized = False
        
        
        self.camera_default_configuration = {'operation_mode':0, 
                                             'sensor_type':0,
                                             'exposure':40, 
                                             'image_poll_timeout_ms':20000, 
                                             'num_frames':2, 
                                             'frames_per_trigger_zero_for_unlimited':1,
                                             'binx':1,'biny':1, 
                                             'black_level':0,
                                             'gain':0,
                                             'Default_ROI':True}
            
        self.set_properties(self.camera_default_configuration)
                
    def set_properties(self, properties):

        
        if 'operation_mode' in properties:
            #0 SOFTWARE_TRIGGER
            self.camera.operation_mode = properties['operation_mode']
        
        if 'sensor_type' in properties:
            self.camera.sensor_type = properties['sensor_type']
            
        if 'ROI' in properties:
            self.camera.roi = self.camera.roi._replace(
            upper_left_x_pixels = properties['ROI']['upper_left_x_pixels'])
            self.camera.roi = self.camera.roi._replace(
            upper_left_y_pixels = properties['ROI']['upper_left_y_pixels'])
            self.camera.roi = self.camera.roi._replace(
            lower_right_x_pixels = properties['ROI']['lower_right_x_pixels'])
            self.camera.roi = self.camera.roi._replace(
            lower_right_y_pixels = properties['ROI']['lower_right_y_pixels'])
            
        
        if 'exposure' in properties:
            exposure_min = self.camera.exposure_time_range_us.min
            exposure_max = self.camera.exposure_time_range_us.max
            
            if int(properties['exposure']) < exposure_min:
                print("WARNING: The minimum exposure value allowed by the camera is " + str(exposure_min) + ".")
                self.camera.exposure_time_us = exposure_min
                
            elif int(properties['exposure']) > exposure_max:
                print("WARNING: The maximum exposure value allowed by the camera is " + str(exposure_max) + ".")
                self.camera.exposure_time_us = exposure_max
                
            else:
                self.camera.exposure_time_us = int(properties['exposure'])
        
        if "image_poll_timeout_ms" in properties:
            self.camera.image_poll_timeout_ms = properties['image_poll_timeout_ms']
                
        if 'binx' in properties: 
            self.camera.binx = properties['binx']
            
        if 'biny' in properties: 
            self.camera.biny = properties['biny']
            
        if 'black_level' in properties:
            black_level_min = self.camera.black_level_range.min
            black_level_max = self.camera.black_level_range.max
            
            if properties['black_level'] < black_level_min:
                print("WARNING: The minimum black level value allowed by the camera is " + str(black_level_min) + ".")
                self.camera.black_level = black_level_min
                
            elif properties['black_level'] > black_level_max:
                print("WARNING: The maximum black level value allowed by the camera is " + str(black_level_max) + ".")
                self.camera.black_level = black_level_max
                
            else:
                self.camera.black_level = properties['black_level']
                
        if 'gain' in properties:
            gain_level_min = self.camera.gain_range.min
            gain_level_max = self.camera.gain_range.max
            
            if properties['gain'] < gain_level_min:
                print("WARNING: The minimum gain level value allowed by the camera is " + str(gain_level_min) + ".")
                self.camera.gain = gain_level_min
                
            elif properties['gain'] > gain_level_max:
                print("WARNING: The maximum gain level value allowed by the camera is " + str(gain_level_max) + ".")
                self.camera.gain = gain_level_max
                
            else:
                self.camera.gain = properties['gain']

        if not self.camera_initialized:
            if 'frames_per_trigger_zero_for_unlimited' in properties:
                self.camera.frames_per_trigger_zero_for_unlimited = properties['frames_per_trigger_zero_for_unlimited']
                
                if ('num_frames' in properties) and (properties['frames_per_trigger_zero_for_unlimited'] > 0): 
                    self.num_frames = properties['frames_per_trigger_zero_for_unlimited']
                else:
                    self.num_frames = properties['num_frames']
                    
        if 'Default_ROI' in properties:
            if properties['Default_ROI']==True:
                self.set_default_roi()
    
    def set_default_roi(self):

        if self.camera_index > 20000:
            ROI_dic = { "upper_left_x_pixels": 0, 
                        "upper_left_y_pixels": 0,
                        "lower_right_x_pixels": 4096 - 1, 
                        "lower_right_y_pixels": 3000 - 1
                    }
        else:

            ROI_dic = { "upper_left_x_pixels": 0, 
                        "upper_left_y_pixels": 0,
                        "lower_right_x_pixels": 1440 - 1, 
                        "lower_right_y_pixels": 1080 - 1
                    }
        
        self.set_properties({'ROI':ROI_dic})
       
    def get_camera_properties(self, ret=False):
        print("\n")
        print("Camera porperties:")
        print("Bith depth:", self.camera.bit_depth)
        print("Operation mode:", self.camera.operation_mode)
        print("Sensor type:", self.camera.sensor_type)
        print("Exposure(us):", self.camera.exposure_time_us)
        print("Black level:", self.camera.black_level)
        print("Frames per trigger:", self.camera.frames_per_trigger_zero_for_unlimited)
        print("Number of frames:", self.num_frames)
        print("Gain:", self.camera.gain)
        print("(binx,biny):", "(" + str(self.camera.binx) + ", " + str(self.camera.biny) + ")")
        print("Image shape(pixels):", "(Height:" + str(self.camera.image_height_pixels) + ", Width:" + str(self.camera.image_width_pixels) + ")")
        print(self.camera.roi)
        print("Image poll timeout(ms):", self.camera.image_poll_timeout_ms)
        print("\n")
        
        if ret:
            pass
        
    def save_properties(self, folder_path):
        
        properties_string = ""
        properties_string += "Camera properties:\n\n"
        
        properties_string += "Bith depth : " + str(self.camera.bit_depth)
        
        properties_string += "\n"
        properties_string += "Operation mode : "
        properties_string += str(self.camera.operation_mode)
        
        properties_string += "\n"
        properties_string += "Sensor type : " + str(self.camera.sensor_type)
        
        properties_string += "\n"
        properties_string += "Exposure(us) : " 
        properties_string += str(self.camera.exposure_time_us)
        
        properties_string += "\n"
        properties_string +="Black level : " + str(self.camera.black_level)
        
        properties_string += "\n"
        if self.camera.frames_per_trigger_zero_for_unlimited==0:
            properties_string +="Frames per trigger: Continuous mode" 
        else:
            properties_string += "Frames per trigger : " 
            properties_string += str(self.camera.frames_per_trigger_zero_for_unlimited)
        
        properties_string += "\n"
        properties_string +="Number of frames : " + str(self.num_frames)
        
        properties_string += "\n"
        properties_string +="Gain : " + str(self.camera.gain)
        
        properties_string += "\n"
        properties_string += "binx, biny : " + "(" + str(self.camera.binx) 
        properties_string += ", " + str(self.camera.biny) + ")"
        
        properties_string += "\n"
        properties_string += "Image shape(pixels) : Height=" 
        properties_string += str(self.camera.image_height_pixels) + ", Width=" 
        properties_string += str(self.camera.image_width_pixels)
        
        properties_string += "\n"
        properties_string += str(self.camera.roi)
        
        properties_string += "\n"
        properties_string += "Image poll timeout(ms) : " 
        properties_string += str(self.camera.image_poll_timeout_ms)
        
        
        properties_string += "\n\nData and time:\n"
        
        tm = time.localtime()
        data_str = str(tm.tm_mday) + "\\" 
        data_str += str(tm.tm_mon) + "\\" + str(tm.tm_year)
        time_str = str(tm.tm_hour) + ":" + str(tm.tm_min)
        
        properties_string += data_str
        properties_string += "\n"
        properties_string += time_str
        
        
        
        path_to_file = folder_path + "\\camera_properties.txt"
        
        file_object = open(path_to_file, "w")
        
        file_object.write(properties_string)
        
        file_object.close()
        
    def get_camera_ready(self):
        # WARN hardcoded -> correct this
        self.camera.arm(2)
        # self.camera.arm(self.num_frames)
        self.camera_initialized = True
    
    def get_image(self):
        
        image_data = []
        self.camera.issue_software_trigger()
        for i in range(self.num_frames):
            
            frame = self.camera.get_pending_frame_or_null()
            if frame is not None:

                frame.image_buffer  # .../ perform operations using the data from image_buffer
                image_buffer_copy = np.copy(frame.image_buffer)
                image_data.append(image_buffer_copy)
                #print(np.shape(image_buffer_copy))
                #print(image_buffer_copy.dtype)
            else:
                print("timeout reached during polling, program exiting...")
                self.camera.disarm()
                break
        
        return np.mean(np.array(image_data),axis=0)/(2**self.camera.bit_depth - 1)
    
    def stop_camera(self):
        self.camera.disarm()
        self.camera_initialized = False
    
    def close(self):
        if self.camera_initialized:
            try:
                self.camera.disarm()
            except self.camera.TLCameraError as e:
                print("TLCameraError: The camera was not armed")
        self.camera.dispose()
        # self.sdk.dispose()
        
        
###############################################################################
#                                                                             #
#                            Ximea cam                                        #
#                                                                             #
###############################################################################
        
class XimeaCam():
    """
    Ximea camera MQ013MG-ON module. Serial number 42650150.
    
    Updatable parameters:
    
    -> exposure: controls single frame exposure time. Set in us. Defaults to 1000us. int;
    -> acq_timing_mode: controls the aquisition timing mode. str
    Defaults to XI_ACQ_TIMING_MODE_FREE_RUN.
    XI_ACQ_TIMING_MODE_FREE_RUN: camera acquires images at a maximum possible framerate
    XI_ACQ_TIMING_MODE_FRAME_RATE: Selects a mode when sensor frame acquisition frequency is set to parameter FRAMERATE
    XI_ACQ_TIMING_MODE_FRAME_RATE_LIMIT: Selects a mode when sensor frame acquisition frequency is limited by parameter FRAMERATE
    
    -> framerate: if the acquisition timing mode is set to other than FREE_RUN, the the framerate is set. int;
    -> gain: Sets the gain of every channel on the camera, set in dB. Actual gain is defined by the closest value
    permited by the hardware. Defaults to 0. float.
    
    -> imgdataformat: sets the image format that the came acquires. Possible values:
    XI_MONO8
    XI_MONO16
    XI_RGB24
    XI_RGB32
    XI_RGB_PLANAR
    XI_RAW8
    XI_RAW16
    XI_FRM_TRANSPORT_DATA
    XI_RGB48
    XI_RGB64
    XI_RGB16_PLANAR
    XI_RAW8x2
    XI_RAW8x4
    XI_RAW16x2
    XI_RAW16x4
    XI_RAW32
    XI_RAW32FLOAT
    
    Altering the image format will alter the numpy data from .get_image() method.
    Defaults to XI_MONO8
    
    ->n_frames: number of frames to take. int 
    ->trigger_source: Defines source of trigger. Default XI_TRG_OFF. str
    XI_TRG_OFF: Capture of next image is automatically started after previous.
    XI_TRG_EDGE_RISING: Capture is started on rising edge of selected input.
    XI_TRG_EDGE_FALLING: Capture is started on falling edge of selected input
    XI_TRG_SOFTWARE: Capture is started with software trigger.
    XI_TRG_LEVEL_HIGH: Specifies that the trigger is considered valid as long as the level of the source signal is high.
    XI_TRG_LEVEL_LOW: Specifies that the trigger is considered valid as long as the level of the source signal is low.
    
    ->trigger_selector: This parameter selects the type of trigger. Default to XI_TRG_SEL_FRAME_START.
    XI_TRG_SEL_FRAME_START: Trigger starts the capture of one frame
    XI_TRG_SEL_EXPOSURE_ACTIVE: Trigger controls the start and length of the exposure.
    XI_TRG_SEL_FRAME_BURST_START: Trigger starts the capture of the bursts of frames in an acquisition.
    XI_TRG_SEL_FRAME_BURST_ACTIVE: Trigger controls the duration of the capture of the bursts of frames in an acquisition.
    XI_TRG_SEL_MULTIPLE_EXPOSURES: Trigger which when first trigger starts exposure and consequent pulses are gating exposure(active HI)
    XI_TRG_SEL_EXPOSURE_START: Trigger controls the start of the exposure of one Frame.
    XI_TRG_SEL_MULTI_SLOPE_PHASE_CHANGE: Trigger controls the multi slope phase in one Frame (phase0 -> phase1) or (phase1 -> phase2).
    XI_TRG_SEL_ACQUISITION_START: Trigger starts acquisition of first frame.
    
    
    ->image_width: sets the image width that the camera will return. Defaults to 1280. The number must be 
    equal to image_width=minimum+N*image_width_increment. image_width_increment is set to 16;
   
    ->image_height: sets the image height that the camera will return. Defaults to 1280. The number must be 
    equal to image_width=minimum+N*image_height_increment. image_height_increment is set to 2;
    
    ->image_offsetX: sets the image offset from origin in the X direction. image_width+image_offsetX must be lower than the
    maximum width (1280). If the value given is not a multiple of the width increment allowed, it is set to the 
    nearest lower integer permitted;
    
    ->image_offsetY: sets the image offset from origin in the Y direction. image_height+image_offsetY must be lower than the
    maximum width (1024). If the value given is not a multiple of the height increment allowed, it is set to the 
    nearest lower integer permitted;
    
    -downsample_mode: defines how we can downsample the output image.
    This model doesn't implement binning, but it does skipping. Possible values:
    XI_DWN_1x1
    XI_DWN_2x2
    
    """
    
    def __init__(self):
        from ximea import xiapi
        
        self.cam=xiapi.Camera()
        self.cam.open_device()
        
        self.cam.set_downsampling_type("XI_SKIPPING")
        self.cam.enable_recent_frame() #Guarantee that the camera gives the most recent frame
        
        
        self.img=xiapi.Image()
        self.img_width_increment=self.cam.get_width_increment()
        self.img_height_increment=self.cam.get_height_increment()
        
        
        
        self.possible_params=["exposure",
                              "acq_timing_mode",
                              "framerate",
                              "gain",
                              "imgdataformat",
                              "n_frames",
                             "trigger_source",
                             "trigger_selector",
                             "image_width",
                             "image_height",
                             "image_offsetX",
                             "image_offsetY",
                             "downsampling_mode",
                             "buffers_queue_size",
                             "buffer_policy"]
        
        self.default_params={"exposure": 50,
                             "acq_timing_mode": "XI_ACQ_TIMING_MODE_FREE_RUN",
                             "framerate": 100,
                             "gain": 0,
                             "imgdataformat":"XI_MONO8",
                             "n_frames":1,
                             "trigger_source":"XI_TRG_OFF",
                             "trigger_selector":"XI_TRG_SEL_FRAME_START",
                             "image_width":self.cam.get_width_maximum(),
                             "image_height":self.cam.get_height_maximum(),
                             "image_offsetX":0,
                             "image_offsetY":0,
                             "downsampling_mode":"XI_DWN_1x1",
                             "buffers_queue_size":self.cam.get_buffers_queue_size_minimum(),
                             "buffer_policy":"XI_BP_UNSAFE"}
        
        
        self.current_params=self.default_params
        self.set_properties(self.current_params)
        
    def set_properties(self, properties):

        self.params_to_update={}
        for key in self.possible_params:
            if key in properties.keys():
                self.params_to_update[key]=properties[key]
            else:
                self.params_to_update[key]=self.current_params[key]
        
        ########Test for params to be within permitted ranges###########
        ## Exposure
        if self.params_to_update["exposure"]<self.cam.get_exposure_minimum():
            print("WARNING: exposure value below permitted one. Setting it to minimum.")
            self.params_to_update["exposure"] = self.cam.get_exposure_minimum()
        elif self.params_to_update["exposure"]>self.cam.get_exposure_maximum():
            print("WARNING: exposure value above permitted one. Setting it to maximum.")
            self.params_to_update["exposure"] = self.cam.get_exposure_maximum()
        
         
        #gain
        if self.params_to_update["gain"]<self.cam.get_gain_minimum():
            print("WARNING: gain value below permitted one. Setting it to minimum.")
            self.params_to_update["gain"] = self.cam.get_gain_minimum()
        elif self.params_to_update["gain"]>self.cam.get_gain_maximum():
            print("WARNING: gain value above permitted one. Setting it to maximum.")
            self.params_to_update["gain"] = self.cam.get_gain_maximum()
        
        #width and X offset
        tmp_N_width=int((self.params_to_update["image_width"]-self.cam.get_width_minimum())/self.img_width_increment)
        tmp_N_offsetX=int(self.params_to_update["image_offsetX"]/self.img_width_increment)
        
        self.params_to_update["image_width"]=self.cam.get_width_minimum()+tmp_N_width*self.img_width_increment
        self.params_to_update["image_offsetX"]=tmp_N_offsetX*self.img_width_increment
        
        if self.params_to_update["image_width"]+self.params_to_update["image_offsetX"]>self.cam.get_width_maximum():
            print("WARNING: width value and offset above permitted one. Setting it to default.")
            self.params_to_update["image_width"] = self.default_params["image_width"]
            self.params_to_update["image_offsetX"] = self.default_params["image_offsetX"]
            
        #height and Y offset
        tmp_N_height=int((self.params_to_update["image_height"]-self.cam.get_height_minimum())/self.img_height_increment)
        tmp_N_offsetY=int(self.params_to_update["image_offsetY"]/self.img_height_increment)
        
        self.params_to_update["image_height"]=self.cam.get_height_minimum()+tmp_N_height*self.img_height_increment
        self.params_to_update["image_offsetY"]=tmp_N_offsetY*self.img_width_increment
        
        if self.params_to_update["image_height"]+self.params_to_update["image_offsetY"]>self.cam.get_height_maximum():
            print("WARNING: height value and Y offset above permitted one. Setting it to default.")
            self.params_to_update["image_height"] = self.default_params["image_height"]
            self.params_to_update["image_offsetY"] = self.default_params["image_offsetY"]
            
        #setting parameters
        self.cam.set_exposure(self.params_to_update["exposure"])
        self.cam.set_acq_timing_mode(self.params_to_update["acq_timing_mode"])
        
        if self.params_to_update["acq_timing_mode"]=="XI_ACQ_TIMING_MODE_FREE_RUN":
            pass
        else:
            self.cam.set_framerate(self.params_to_update["framerate"])
        
        #framerate
        if self.params_to_update["acq_timing_mode"]=="XI_ACQ_TIMING_MODE_FREE_RUN":
            pass
        else:
            if self.params_to_update["framerate"]<self.cam.get_framerate_minimum():
                print("WARNING: framerate value below permitted one. Setting it to minimum.")
                self.params_to_update["framerate"] = self.cam.get_framerate_minimum()
            elif self.params_to_update["framerate"]>self.cam.get_framerate_maximum():
                print("WARNING: framerate value above permitted one. Setting it to maximum.")
                self.params_to_update["framerate"] = self.cam.get_framerate_maximum()
                
        self.cam.set_gain(self.params_to_update["gain"])
        self.cam.set_imgdataformat(self.params_to_update["imgdataformat"])
        self.cam.set_trigger_source(self.params_to_update["trigger_source"])
        self.cam.set_trigger_selector(self.params_to_update["trigger_selector"])
        self.cam.set_width(self.params_to_update["image_width"])
        self.cam.set_height(self.params_to_update["image_height"])
        self.cam.set_offsetX(self.params_to_update["image_offsetX"])
        self.cam.set_offsetY(self.params_to_update["image_offsetY"])
        self.cam.set_downsampling(self.params_to_update["downsampling_mode"])
        self.cam.set_buffers_queue_size(self.params_to_update["buffers_queue_size"])
        self.cam.set_buffer_policy(self.params_to_update["buffer_policy"])
        
        self.current_params["exposure"]=self.cam.get_exposure()
        self.current_params["acq_timing_mode"]=self.cam.get_acq_timing_mode()
        self.current_params["framerate"]=self.cam.get_framerate()
        self.current_params["gain"]=self.cam.get_gain()
        self.current_params["imgdataformat"]=self.cam.get_imgdataformat()
        self.current_params["n_frames"]=self.params_to_update["n_frames"]
        self.current_params["trigger_source"]=self.cam.get_trigger_source()
        self.current_params["trigger_selector"]=self.cam.get_trigger_selector()
        self.current_params["image_width"]=self.cam.get_width()
        self.current_params["image_height"]=self.cam.get_height()
        self.current_params["image_offsetX"]=self.cam.get_offsetX()
        self.current_params["image_offsetY"]=self.cam.get_offsetY()
        self.current_params["downsampling_mode"]=self.cam.get_downsampling()
        self.current_params["buffers_queue_size"]=self.cam.get_buffers_queue_size()
        self.current_params["buffer_policy"]=self.cam.get_buffer_policy()
        
    def set_default_roi(self):
        properties={"image_width":self.cam.get_width_maximum(),
                    "image_height":self.cam.get_height_maximum(),
                    "image_offsetX":0,
                    "image_offsetY":0}
        self.set_properties(properties)
        
       
    def get_camera_properties(self, ret=False):
        print("--------------------------------------------------------------------------")
        print("exposure: {}us".format(self.current_params["exposure"]))
        print("acq_timing_mode: {}".format(self.current_params["acq_timing_mode"]))
        print("framerate: {}".format(self.current_params["framerate"]))
        print("gain: {}dB".format(self.current_params["gain"]))
        print("imgdataformat: {}".format(self.current_params["imgdataformat"]))
        print("n_frames: {}".format(self.current_params["n_frames"]))
        print("trigger_source: {}".format(self.current_params["trigger_source"]))
        print("image_width: {}".format(self.current_params["image_width"]))
        print("image_height: {}".format(self.current_params["image_height"]))
        print("image_offsetX: {}".format(self.current_params["image_offsetX"]))
        print("image_offsetY: {}".format(self.current_params["image_offsetY"]))
        print("downsampling_mode: {}".format(self.current_params["downsampling_mode"]))
        print("buffers_queue_size: {}".format(self.current_params["buffers_queue_size"]))
        print("buffer_policy: {}".format(self.current_params["buffer_policy"]))
        print("--------------------------------------------------------------------------")
        print(self.cam.is_recent_frame())
        
        if ret:
            return self.current_params
    
    def save_properties(self, path):
        log=open(path+r"\\log.txt", "w")
        log.write("Camera name: XIMEA \n")
        
        
        
        cam_params=self.current_params
        for param in cam_params.keys():
            log.write("{} : {} \n".format(param,cam_params[param]))
         
        properties_string= "\n\nData and time:\n"
        
        tm = time.localtime()
        data_str = str(tm.tm_mday) + "\\" 
        data_str += str(tm.tm_mon) + "\\" + str(tm.tm_year)
        time_str = str(tm.tm_hour) + ":" + str(tm.tm_min)
        
        properties_string += data_str
        properties_string += "\n"
        properties_string += time_str
        
        log.write(properties_string)
        
        log.close()    
        
    def get_camera_ready(self):
        self.cam.start_acquisition()
        
    def get_image(self):
        n_blanck=0
        
        if "MONO" not in self.current_params["imgdataformat"]:
            images=[]

            if self.current_params["trigger_source"]=="XI_TRG_OFF":
                for i in range(self.current_params["n_frames"]+n_blanck):
                    self.cam.get_image(self.img)
                    
                    images.append(self.img.get_image_data_numpy().astype(float))
            elif self.current_params["trigger_source"]=="XI_TRG_SOFTWARE" and self.current_params["trigger_selector"]=="XI_TRG_SEL_FRAME_START":
                for i in range(self.current_params["n_frames"]+n_blanck):
                    self.cam.set_trigger_software(1)
                    self.cam.get_image(self.img)
                    images.append(self.img.get_image_data_numpy().astype(float))
                
            images=np.asarray(images)
            
            avg_img=np.mean(images[n_blanck:],axis=0)
            
                
        else:
            images=np.zeros((self.current_params["n_frames"]+n_blanck,self.current_params["image_height"],self.current_params["image_width"]), dtype=int)
            
            if self.current_params["trigger_source"]=="XI_TRG_OFF":
                for i in range(self.current_params["n_frames"]+n_blanck):
                   self.cam.get_image(self.img)
                   images[i]=self.img.get_image_data_numpy().astype(float)
                    
            elif self.current_params["trigger_source"]=="XI_TRG_SOFTWARE" and self.current_params["trigger_selector"]=="XI_TRG_SEL_FRAME_START":
                for i in range(self.current_params["n_frames"]+n_blanck):
                    self.cam.set_trigger_software(1)
                    self.cam.get_image(self.img)
                    
                    images[i]=self.img.get_image_data_numpy().astype(float)
                    
            avg_img=np.mean(images[n_blanck:],axis=0)
            
            if self.current_params["imgdataformat"]=="XI_MONO8":
                avg_img=avg_img/(2**8-1)
            elif self.current_params["imgdataformat"]=="XI_MONO16":
                avg_img=avg_img/(2**10-1)
                
        return avg_img
    
    def stop_camera(self):
        self.cam.stop_acquisition()
        
    def close(self):
        self.cam.close_device()
        self.cam=None
        
        
###############################################################################
#                                                                             #
#                            IDS cam                                          #
#                                                                             #
###############################################################################


class IdsCam():

    from pyueye import ueye
    
    
    _is_SetExposureTime = ueye._bind("is_SetExposureTime",
                                     [ueye.ctypes.c_uint, ueye.ctypes.c_double,
                                      ueye.ctypes.POINTER(ueye.ctypes.c_double)], ueye.ctypes.c_int)
    IS_GET_EXPOSURE_TIME = 0x8000

    @staticmethod
    def is_SetExposureTime(hCam, EXP, newEXP):
        """
        Description

        The function is_SetExposureTime() sets the with EXP indicated exposure time in ms. Since this
        is adjustable only in multiples of the time, a line needs, the actually used time can deviate from
        the desired value.

        The actual duration adjusted after the call of this function is readout with the parameter newEXP.
        By changing the window size or the readout timing (pixel clock) the exposure time set before is changed also.
        Therefore is_SetExposureTime() must be called again thereafter.

        Exposure-time interacting functions:
            - is_SetImageSize()
            - is_SetPixelClock()
            - is_SetFrameRate() (only if the new image time will be shorter than the exposure time)

        Which minimum and maximum values are possible and the dependence of the individual
        sensors is explained in detail in the description to the uEye timing.

        Depending on the time of the change of the exposure time this affects only with the recording of
        the next image.

        :param hCam: c_uint (aka c-type: HIDS)
        :param EXP: c_double (aka c-type: DOUBLE) - New desired exposure-time.
        :param newEXP: c_double (aka c-type: double *) - Actual exposure time.
        :returns: IS_SUCCESS, IS_NO_SUCCESS

        Notes for EXP values:

        - IS_GET_EXPOSURE_TIME Returns the actual exposure-time through parameter newEXP.
        - If EXP = 0.0 is passed, an exposure time of (1/frame rate) is used.
        - IS_GET_DEFAULT_EXPOSURE Returns the default exposure time newEXP Actual exposure time
        - IS_SET_ENABLE_AUTO_SHUTTER : activates the AutoExposure functionality.
          Setting a value will deactivate the functionality.
          (see also 4.86 is_SetAutoParameter).
          
          method adapted from: https://stackoverflow.com/questions/68239400/ids-cameras-pyueye-python-package-set-exposure-parameter-is-setautoparameter-f
        """
        _hCam = ueye._value_cast(hCam, ueye.ctypes.c_uint)
        _EXP = ueye._value_cast(EXP, ueye.ctypes.c_double)
        ret = IdsCam._is_SetExposureTime(_hCam, _EXP, ueye.ctypes.byref(newEXP) if newEXP is not None else None)
        return ret
    

    
    def __init__(self, camera_index=0):
        
        self.camera_index = camera_index
        self.hCam = self.ueye.HIDS(self.camera_index)  # 0: first available camera;  1-254: The camera with the specified camera ID
        self.sInfo = self.ueye.SENSORINFO()
        self.cInfo = self.ueye.CAMINFO()
        self.pcImageMemory = self.ueye.c_mem_p()
        self.MemID = self.ueye.int()
        self.rectAOI = self.ueye.IS_RECT()
        self.pitch = self.ueye.INT()
        self.nBitsPerPixel = self.ueye.INT(10)  # 24: bits per pixel for color mode; take 8 bits per pixel for monochrome
        self.channels = 1  # 3: channels for color mode(RGB); take 1 channel for monochromeq
        self.m_nColorMode = self.ueye.INT()  # Y8/RGB16/RGB24/REG32
        self.bytes_per_pixel = int(self.nBitsPerPixel / 8)
        self.refPt = [(0,1),(2,3)]
        





        # Starts the driver and establishes the connection to the camera
        nRet = self.ueye.is_InitCamera(self.hCam, None)
        if nRet != self.ueye.IS_SUCCESS:
            print("is_InitCamera ERROR")

        # Reads out the data hard-coded in the non-volatile camera memory and writes it to the data structure that cInfo points to
        nRet = self.ueye.is_GetCameraInfo(self.hCam, self.cInfo)
        if nRet != self.ueye.IS_SUCCESS:
            print("is_GetCameraInfo ERROR")

        # You can query additional information about the sensor type used in the camera
        nRet = self.ueye.is_GetSensorInfo(self.hCam, self.sInfo)
        if nRet != self.ueye.IS_SUCCESS:
            print("is_GetSensorInfo ERROR")

        nRet = self.ueye.is_ResetToDefault(self.hCam)
        if nRet != self.ueye.IS_SUCCESS:
            print("is_ResetToDefault ERROR")

        # Set display mode to DIB
        nRet = self.ueye.is_SetDisplayMode(self.hCam, self.ueye.IS_SET_DM_DIB)

        self.m_nColorMode = self.ueye.IS_CM_MONO8
        self.nBitsPerPixel = self.ueye.INT(8)
        self.bytes_per_pixel = int(self.nBitsPerPixel / 8)

        # Can be used to set the size and position of an "area of interest"(AOI) within an image
        nRet = self.ueye.is_AOI(self.hCam, self.ueye.IS_AOI_IMAGE_GET_AOI, self.rectAOI, self.ueye.sizeof(self.rectAOI))
        if nRet != self.ueye.IS_SUCCESS:
            print("is_AOI ERROR")

        self.width = self.rectAOI.s32Width
        self.height = self.rectAOI.s32Height

        gamma_value = self.ueye.uint(int(1*100)) # 1.0*100
        nRet = self.ueye.is_Gamma(self.hCam, self.ueye.IS_GAMMA_CMD_SET, gamma_value, self.ueye.sizeof(gamma_value))
        if nRet != self.ueye.IS_SUCCESS:
            print("gamma value ERROR")

        nRet = self.ueye.is_SetHardwareGamma(self.hCam, self.ueye.IS_SET_HW_GAMMA_OFF)
        if nRet != self.ueye.IS_SUCCESS:
            print("Hardware gamma ERROR")

        blacklevel_offset = self.ueye.uint(0)
        nRet = self.ueye.is_Blacklevel(self.hCam, self.ueye.IS_BLACKLEVEL_CMD_SET_OFFSET, blacklevel_offset, self.ueye.sizeof(blacklevel_offset))
        if nRet != self.ueye.IS_SUCCESS:
            print("Black level offset ERROR")

        blacklevel_auto = self.ueye.uint(1)
        nRet = self.ueye.is_Blacklevel(self.hCam, self.ueye.IS_BLACKLEVEL_CMD_SET_MODE, blacklevel_auto, self.ueye.sizeof(blacklevel_auto))
        if nRet != self.ueye.IS_SUCCESS:
            print("Black level auto ERROR")

        # nRet = self.ueye.is_SetWhiteBalance(self.hCam, self.ueye.IS_SET_WB_DISABLE)
        # if nRet != self.ueye.IS_SUCCESS:
        #     print("White balacen auto ERROR")

        self.camera_initialized = True
                

    
    def set_camera_exposure(self, level_us):
        """
        :param level_us: exposure level in micro-seconds, or zero for auto exposure
        
        note that you can never exceed 1000000/fps, but it is possible to change the fps
        """
        p1 = self.ueye.DOUBLE()
        if level_us == 0:
            rc = IdsCam._is_SetExposureTime(self.hCam, self.ueye.IS_SET_ENABLE_AUTO_SHUTTER, p1)
            print(f'set_camera_exposure: set to auto')
        else:
            ms = self.ueye.DOUBLE(level_us / 1000)
            rc = IdsCam._is_SetExposureTime(self.hCam, ms, p1)
            print(f'set_camera_exposure: requested {ms.value}, got {p1.value}', end='\r')
            
    def set_properties(self, properties):
        if 'exposure' in properties:
            self.set_camera_exposure(properties['exposure'])
   
        
    def get_camera_ready(self):
        # Allocates an image memory for an image having its dimensions defined by width and height and its color depth defined by nBitsPerPixel
        nRet = self.ueye.is_AllocImageMem(self.hCam, self.width, self.height, self.nBitsPerPixel, self.pcImageMemory, self.MemID)
        if nRet != self.ueye.IS_SUCCESS:
            print("is_AllocImageMem ERROR")
        else:
            # Makes the specified image memory the active memory
            nRet = self.ueye.is_SetImageMem(self.hCam, self.pcImageMemory, self.MemID)
            if nRet != self.ueye.IS_SUCCESS:
                print("is_SetImageMem ERROR")
            else:
                # Set the desired color mode
                nRet = self.ueye.is_SetColorMode(self.hCam, self.m_nColorMode)

        # Activates the camera's live video mode (free run mode)
        nRet = self.ueye.is_CaptureVideo(self.hCam, self.ueye.IS_WAIT)
        # nRet = self.ueye.is_Trigger(self.hCam)
        if nRet != self.ueye.IS_SUCCESS:
            # print("is_CaptureVideo ERROR")
            pass

        # Enables the queue mode for existing image memory sequences
        self.nRet = self.ueye.is_InquireImageMem(self.hCam, self.pcImageMemory, self.MemID, self.width, self.height, self.nBitsPerPixel, self.pitch)
        if self.nRet != self.ueye.IS_SUCCESS:
            print("is_InquireImageMem ERROR")
        else:
            #print("Press q to leave the programm")
            pass
        
        time.sleep(1)
        
        #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
        #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
        #del test_out
        
    
    def get_image(self):
        ms = self.ueye.DOUBLE(20)
        frame = np.zeros((self.height.value, self.width.value))
        nshots = 1
        counter = 0
        #time.sleep(1)
        for i in range(0, nshots):
            if self.nRet == self.ueye.IS_SUCCESS:
                array = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
                # frame += np.reshape(array.astype(np.float16), (self.height.value, self.width.value))
                frame = np.reshape(array.astype(np.float32), (self.height.value, self.width.value))
                #print(np.max(array.astype(np.float16)))
                #print("\n")
                counter += 1
        counter = 1
        return np.array(frame)/counter/255.0
    
    def stop_camera(self):
        if not self.camera_initialized:
            self.camera_initialized = False
    
    def close(self):
        self.ueye.is_ExitCamera(self.hCam)
        if not self.camera_initialized:
            self.camera_initialized = False
            
    #Save the camera current properties
    def save_properties(self, folder_path):
        print("Method not yet implemented for the IDS camera!")
        
    def get_properties(self, ret=False):
        print("Method not yet implemented for the IDS camera!")


# class IdsCamOld():

#     from pyueye import ueye
    
    
#     _is_SetExposureTime = ueye._bind("is_SetExposureTime",
#                                      [ueye.ctypes.c_uint, ueye.ctypes.c_double,
#                                       ueye.ctypes.POINTER(ueye.ctypes.c_double)], ueye.ctypes.c_int)
#     IS_GET_EXPOSURE_TIME = 0x8000

#     @staticmethod
#     def is_SetExposureTime(hCam, EXP, newEXP):
#         """
#         Description

#         The function is_SetExposureTime() sets the with EXP indicated exposure time in ms. Since this
#         is adjustable only in multiples of the time, a line needs, the actually used time can deviate from
#         the desired value.

#         The actual duration adjusted after the call of this function is readout with the parameter newEXP.
#         By changing the window size or the readout timing (pixel clock) the exposure time set before is changed also.
#         Therefore is_SetExposureTime() must be called again thereafter.

#         Exposure-time interacting functions:
#             - is_SetImageSize()
#             - is_SetPixelClock()
#             - is_SetFrameRate() (only if the new image time will be shorter than the exposure time)

#         Which minimum and maximum values are possible and the dependence of the individual
#         sensors is explained in detail in the description to the uEye timing.

#         Depending on the time of the change of the exposure time this affects only with the recording of
#         the next image.

#         :param hCam: c_uint (aka c-type: HIDS)
#         :param EXP: c_double (aka c-type: DOUBLE) - New desired exposure-time.
#         :param newEXP: c_double (aka c-type: double *) - Actual exposure time.
#         :returns: IS_SUCCESS, IS_NO_SUCCESS

#         Notes for EXP values:

#         - IS_GET_EXPOSURE_TIME Returns the actual exposure-time through parameter newEXP.
#         - If EXP = 0.0 is passed, an exposure time of (1/frame rate) is used.
#         - IS_GET_DEFAULT_EXPOSURE Returns the default exposure time newEXP Actual exposure time
#         - IS_SET_ENABLE_AUTO_SHUTTER : activates the AutoExposure functionality.
#           Setting a value will deactivate the functionality.
#           (see also 4.86 is_SetAutoParameter).
          
#           method adapted from: https://stackoverflow.com/questions/68239400/ids-cameras-pyueye-python-package-set-exposure-parameter-is-setautoparameter-f
#         """
#         _hCam = ueye._value_cast(hCam, ueye.ctypes.c_uint)
#         _EXP = ueye._value_cast(EXP, ueye.ctypes.c_double)
#         ret = IdsCam._is_SetExposureTime(_hCam, _EXP, ueye.ctypes.byref(newEXP) if newEXP is not None else None)
#         return ret
    

    
#     def __init__(self, camera_index=0):
        
#         self.camera_index = camera_index
#         self.hCam = self.ueye.HIDS(self.camera_index)  # 0: first available camera;  1-254: The camera with the specified camera ID
#         self.sInfo = self.ueye.SENSORINFO()
#         self.cInfo = self.ueye.CAMINFO()
#         self.pcImageMemory = self.ueye.c_mem_p()
#         self.MemID = self.ueye.int()
#         self.rectAOI = self.ueye.IS_RECT()
#         self.pitch = self.ueye.INT()
#         self.nBitsPerPixel = self.ueye.INT(10)  # 24: bits per pixel for color mode; take 8 bits per pixel for monochrome
#         self.channels = 1  # 3: channels for color mode(RGB); take 1 channel for monochromeq
#         self.m_nColorMode = self.ueye.INT()  # Y8/RGB16/RGB24/REG32
#         self.bytes_per_pixel = int(self.nBitsPerPixel / 8)
#         self.refPt = [(0,1),(2,3)]
        





#         # Starts the driver and establishes the connection to the camera
#         nRet = self.ueye.is_InitCamera(self.hCam, None)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_InitCamera ERROR")

#         # Reads out the data hard-coded in the non-volatile camera memory and writes it to the data structure that cInfo points to
#         nRet = self.ueye.is_GetCameraInfo(self.hCam, self.cInfo)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_GetCameraInfo ERROR")

#         # You can query additional information about the sensor type used in the camera
#         nRet = self.ueye.is_GetSensorInfo(self.hCam, self.sInfo)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_GetSensorInfo ERROR")

#         nRet = self.ueye.is_ResetToDefault(self.hCam)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_ResetToDefault ERROR")

#         # Set display mode to DIB
#         nRet = self.ueye.is_SetDisplayMode(self.hCam, self.ueye.IS_SET_DM_DIB)

#         self.m_nColorMode = self.ueye.IS_CM_MONO8
#         self.nBitsPerPixel = self.ueye.INT(8)
#         self.bytes_per_pixel = int(self.nBitsPerPixel / 8)

#         # Can be used to set the size and position of an "area of interest"(AOI) within an image
#         nRet = self.ueye.is_AOI(self.hCam, self.ueye.IS_AOI_IMAGE_GET_AOI, self.rectAOI, self.ueye.sizeof(self.rectAOI))
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_AOI ERROR")

#         self.width = self.rectAOI.s32Width
#         self.height = self.rectAOI.s32Height

#         self.camera_initialized = True
                

    
#     def set_camera_exposure(self, level_us):
#         """
#         :param level_us: exposure level in micro-seconds, or zero for auto exposure
        
#         note that you can never exceed 1000000/fps, but it is possible to change the fps
#         """
#         p1 = self.ueye.DOUBLE()
#         if level_us == 0:
#             rc = IdsCam._is_SetExposureTime(self.hCam, self.ueye.IS_SET_ENABLE_AUTO_SHUTTER, p1)
#             print(f'set_camera_exposure: set to auto')
#         else:
#             ms = self.ueye.DOUBLE(level_us / 1000)
#             rc = IdsCam._is_SetExposureTime(self.hCam, ms, p1)
#             print(f'set_camera_exposure: requested {ms.value}, got {p1.value}', end='\r')
            
#     def set_properties(self, properties):
#         if 'exposure' in properties:
#             self.set_camera_exposure(properties['exposure'])
   
        
#     def get_camera_ready(self):
#         # Allocates an image memory for an image having its dimensions defined by width and height and its color depth defined by nBitsPerPixel
#         nRet = self.ueye.is_AllocImageMem(self.hCam, self.width, self.height, self.nBitsPerPixel, self.pcImageMemory, self.MemID)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_AllocImageMem ERROR")
#         else:
#             # Makes the specified image memory the active memory
#             nRet = self.ueye.is_SetImageMem(self.hCam, self.pcImageMemory, self.MemID)
#             if nRet != self.ueye.IS_SUCCESS:
#                 print("is_SetImageMem ERROR")
#             else:
#                 # Set the desired color mode
#                 nRet = self.ueye.is_SetColorMode(self.hCam, self.m_nColorMode)

#         # Activates the camera's live video mode (free run mode)
#         nRet = self.ueye.is_CaptureVideo(self.hCam, self.ueye.IS_WAIT)
#         # nRet = self.ueye.is_Trigger(self.hCam)
#         if nRet != self.ueye.IS_SUCCESS:
#             # print("is_CaptureVideo ERROR")
#             pass

#         # Enables the queue mode for existing image memory sequences
#         self.nRet = self.ueye.is_InquireImageMem(self.hCam, self.pcImageMemory, self.MemID, self.width, self.height, self.nBitsPerPixel, self.pitch)
#         if self.nRet != self.ueye.IS_SUCCESS:
#             print("is_InquireImageMem ERROR")
#         else:
#             #print("Press q to leave the programm")
#             pass
        
#         time.sleep(1)
        
#         #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
#         #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
#         #del test_out
        
    
#     def get_image(self):
#         ms = self.ueye.DOUBLE(20)
#         frame = np.zeros((self.height.value, self.width.value))
#         nshots = 4
#         counter = 0
#         #time.sleep(1)
#         for i in range(0, nshots):
#             if self.nRet == self.ueye.IS_SUCCESS:
#                 array = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
#                 # frame += np.reshape(array.astype(np.float16), (self.height.value, self.width.value))
#                 frame = np.reshape(array.astype(np.float32), (self.height.value, self.width.value))
#                 #print(np.max(array.astype(np.float16)))
#                 #print("\n")
#                 counter += 1
#         counter = 1
#         return np.array(frame)/counter/255.0
    
#     def stop_camera(self):
#         if not self.camera_initialized:
#             self.camera_initialized = False
    
#     def close(self):
#         self.ueye.is_ExitCamera(self.hCam)
#         if not self.camera_initialized:
#             self.camera_initialized = False
            
#     #Save the camera current properties
#     def save_properties(self, folder_path):
#         print("Method not yet implemented for the IDS camera!")
        
#     def get_properties(self, ret=False):
#         print("Method not yet implemented for the IDS camera!")


# class IdsCam():

#     from pyueye import ueye
    
    
    
#     _is_SetExposureTime = ueye._bind("is_SetExposureTime",
#                                      [ueye.ctypes.c_uint, ueye.ctypes.c_double,
#                                       ueye.ctypes.POINTER(ueye.ctypes.c_double)], ueye.ctypes.c_int)
#     IS_GET_EXPOSURE_TIME = 0x8000

#     @staticmethod
#     def is_SetExposureTime(hCam, EXP, newEXP):
#         """
#         Description

#         The function is_SetExposureTime() sets the with EXP indicated exposure time in ms. Since this
#         is adjustable only in multiples of the time, a line needs, the actually used time can deviate from
#         the desired value.

#         The actual duration adjusted after the call of this function is readout with the parameter newEXP.
#         By changing the window size or the readout timing (pixel clock) the exposure time set before is changed also.
#         Therefore is_SetExposureTime() must be called again thereafter.

#         Exposure-time interacting functions:
#             - is_SetImageSize()
#             - is_SetPixelClock()
#             - is_SetFrameRate() (only if the new image time will be shorter than the exposure time)

#         Which minimum and maximum values are possible and the dependence of the individual
#         sensors is explained in detail in the description to the uEye timing.

#         Depending on the time of the change of the exposure time this affects only with the recording of
#         the next image.

#         :param hCam: c_uint (aka c-type: HIDS)
#         :param EXP: c_double (aka c-type: DOUBLE) - New desired exposure-time.
#         :param newEXP: c_double (aka c-type: double *) - Actual exposure time.
#         :returns: IS_SUCCESS, IS_NO_SUCCESS

#         Notes for EXP values:

#         - IS_GET_EXPOSURE_TIME Returns the actual exposure-time through parameter newEXP.
#         - If EXP = 0.0 is passed, an exposure time of (1/frame rate) is used.
#         - IS_GET_DEFAULT_EXPOSURE Returns the default exposure time newEXP Actual exposure time
#         - IS_SET_ENABLE_AUTO_SHUTTER : activates the AutoExposure functionality.
#           Setting a value will deactivate the functionality.
#           (see also 4.86 is_SetAutoParameter).
          
#           method adapted from: https://stackoverflow.com/questions/68239400/ids-cameras-pyueye-python-package-set-exposure-parameter-is-setautoparameter-f
#         """
#         _hCam = ueye._value_cast(hCam, ueye.ctypes.c_uint)
#         _EXP = ueye._value_cast(EXP, ueye.ctypes.c_double)
#         ret = IdsCam._is_SetExposureTime(_hCam, _EXP, ueye.ctypes.byref(newEXP) if newEXP is not None else None)
#         return ret
    

    
#     def __init__(self, camera_index=0):
        
#         self.camera_index = camera_index
#         self.hCam = self.ueye.HIDS(self.camera_index)  # 0: first available camera;  1-254: The camera with the specified camera ID
#         self.sInfo = self.ueye.SENSORINFO()
#         self.cInfo = self.ueye.CAMINFO()
#         self.pcImageMemory = self.ueye.c_mem_p()
#         self.MemID = self.ueye.int()
#         self.rectAOI = self.ueye.IS_RECT()
#         self.pitch = self.ueye.INT()
#         self.nBitsPerPixel = self.ueye.INT(10)  # 24: bits per pixel for color mode; take 8 bits per pixel for monochrome
#         self.channels = 1  # 3: channels for color mode(RGB); take 1 channel for monochromeq
#         self.m_nColorMode = self.ueye.INT()  # Y8/RGB16/RGB24/REG32
#         self.bytes_per_pixel = int(self.nBitsPerPixel / 8)
#         self.refPt = [(0,1),(2,3)]
#         self.nShutterMode = ctypes.c_int(self.ueye.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START)
#         self.ueye.is_DeviceFeature(self.hCam, 
#                                    self.ueye.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START,
#                                    pParam=self.nShutterMode,
#                                    cbSizeOfParam=self.ueye.sizeof(self.nShutterMode))
        
#         self.IS_SET_TRIGGER_SOFTWARE = ctypes.c_uint(0x1000)
#         nRet = self.ueye.is_SetExternalTrigger(self.hCam, self.IS_SET_TRIGGER_SOFTWARE)


#         self.ueye.IS_SEQUENCER_CONFIGURATION_LOAD()
        

#         self.ImageData: np.ndarray



#         # Starts the driver and establishes the connection to the camera
#         nRet = self.ueye.is_InitCamera(self.hCam, None)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_InitCamera ERROR")

#         # Reads out the data hard-coded in the non-volatile camera memory and writes it to the data structure that cInfo points to
#         nRet = self.ueye.is_GetCameraInfo(self.hCam, self.cInfo)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_GetCameraInfo ERROR")

#         # You can query additional information about the sensor type used in the camera
#         nRet = self.ueye.is_GetSensorInfo(self.hCam, self.sInfo)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_GetSensorInfo ERROR")

#         nRet = self.ueye.is_ResetToDefault(self.hCam)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_ResetToDefault ERROR")

#         # Set display mode to DIB
#         nRet = self.ueye.is_SetDisplayMode(self.hCam, self.ueye.IS_SET_DM_DIB)

#         self.m_nColorMode = self.ueye.IS_CM_MONO8
#         self.nBitsPerPixel = self.ueye.INT(8)
#         self.bytes_per_pixel = int(self.nBitsPerPixel / 8)

#         # Can be used to set the size and position of an "area of interest"(AOI) within an image
#         nRet = self.ueye.is_AOI(self.hCam, self.ueye.IS_AOI_IMAGE_GET_AOI, self.rectAOI, self.ueye.sizeof(self.rectAOI))
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_AOI ERROR")

#         self.width = self.rectAOI.s32Width
#         self.height = self.rectAOI.s32Height

#         self.camera_initialized = True
                
# #     def set_properties(self, properties):

        
# #         if 'operation_mode' in properties:
# #             #0 SOFTWARE_TRIGGER
# #             self.camera.operation_mode = properties['operation_mode']
        
# #         if 'sensor_type' in properties:
# #             self.camera.sensor_type = properties['sensor_type']
            
# #         if 'ROI' in properties:
# #             self.camera.roi = self.camera.roi._replace(
# #             upper_left_x_pixels = properties['ROI']['upper_left_x_pixels'])
# #             self.camera.roi = self.camera.roi._replace(
# #             upper_left_y_pixels = properties['ROI']['upper_left_y_pixels'])
# #             self.camera.roi = self.camera.roi._replace(
# #             lower_right_x_pixels = properties['ROI']['lower_right_x_pixels'])
# #             self.camera.roi = self.camera.roi._replace(
# #             lower_right_y_pixels = properties['ROI']['lower_right_y_pixels'])
    
#     def set_camera_exposure(self, level_us):
#         """
#         :param level_us: exposure level in micro-seconds, or zero for auto exposure
        
#         note that you can never exceed 1000000/fps, but it is possible to change the fps
#         """
#         p1 = self.ueye.DOUBLE()
#         if level_us == 0:
#             rc = IdsCam._is_SetExposureTime(self.hCam, self.ueye.IS_SET_ENABLE_AUTO_SHUTTER, p1)
#             print(f'set_camera_exposure: set to auto')
#         else:
#             ms = self.ueye.DOUBLE(level_us / 1000)
#             rc = IdsCam._is_SetExposureTime(self.hCam, ms, p1)
#             print(f'set_camera_exposure: requested {ms.value}, got {p1.value}', end='\r')

#             self.ueye.is_DeviceFeature(self.hCam, 
#                                    self.ueye.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START,
#                                    pParam=self.nShutterMode,
#                                    cbSizeOfParam=self.ueye.sizeof(self.nShutterMode))


#     def set_properties(self, properties):
#         if 'exposure' in properties:
#             self.set_camera_exposure(properties['exposure'])
   
        
#     def get_camera_ready(self):
#         # Allocates an image memory for an image having its dimensions defined by width and height and its color depth defined by nBitsPerPixel
#         nRet = self.ueye.is_AllocImageMem(self.hCam, self.width, self.height, self.nBitsPerPixel, self.pcImageMemory, self.MemID)
#         if nRet != self.ueye.IS_SUCCESS:
#             print("is_AllocImageMem ERROR")
#         else:
#             # Makes the specified image memory the active memory
#             nRet = self.ueye.is_SetImageMem(self.hCam, self.pcImageMemory, self.MemID)
#             if nRet != self.ueye.IS_SUCCESS:
#                 print("is_SetImageMem ERROR")
#             else:
#                 # Set the desired color mode
#                 nRet = self.ueye.is_SetColorMode(self.hCam, self.m_nColorMode)

#         # nRet = self.ueye.is_FreezeVideo

#         # # Activates the camera's live video mode (free run mode)
#         # nRet = self.ueye.is_CaptureVideo(self.hCam, self.ueye.IS_WAIT)
#         # # nRet = self.ueye.is_Trigger(self.hCam)
#         # if nRet != self.ueye.IS_SUCCESS:
#         #     # print("is_CaptureVideo ERROR")
#         #     pass

#         # Enables the queue mode for existing image memory sequences
#         self.nRet = self.ueye.is_InquireImageMem(self.hCam, self.pcImageMemory, self.MemID, self.width, self.height, self.nBitsPerPixel, self.pitch)
#         if self.nRet != self.ueye.IS_SUCCESS:
#             print("is_InquireImageMem ERROR")
#         else:
#             #print("Press q to leave the programm")
#             pass
        
#         time.sleep(1)
        
#         #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
#         #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
#         #del test_out
        
    
#     def get_image(self):
#         self.pid = ctypes.c_int()
#         self.pcImMemory = ctypes.c_char_p()
#         self.ueye.is_AllocImageMem(self.hCam, ctypes.c_int(self.width.value), 
#                                               ctypes.c_int(self.height.value), 
#                                               ctypes.c_int(self.bytes_per_pixel), 
#                                               ctypes.byref(self.pcImMemory), 
#                                               ctypes.byref(self.pid))
        
#         # self.ueye.is_SetImageMem(self.hCam, self.pcImMemory, self.pid)

#         ImageData = np.ones((self.height.value, self.width.value), dtype=np.uint8)
#         nshots = 1

#         frame = 0
        
#         for i in range(0, nshots):
#             if self.nRet == self.ueye.IS_SUCCESS:
#                 self.ueye.is_FreezeVideo(self.hCam, ctypes.c_int(0x0000))  #IS_DONT_WAIT  = 0x0000, or IS_GET_LIVE = 0x8000
#                 time.sleep(0.5)
#                 array = self.ueye.is_CopyImageMem(self.hCam, self.pcImMemory, self.pid, ImageData.ctypes.data)
#                 # frame = np.reshape(array.astype(np.float16), (self.height.value, self.width.value))

#                 # array = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
#                 # # frame += np.reshape(array.astype(np.float16), (self.height.value, self.width.value))
#                 # frame = np.reshape(array.astype(np.float32), (self.height.value, self.width.value))
#                 # #print(np.max(array.astype(np.float16)))
#                 # #print("\n")
#                 # counter += 1
#         counter = 1
#         return array
    
#     def stop_camera(self):
#         if not self.camera_initialized:
#             self.camera_initialized = False
    
#     def close(self):
#         self.ueye.is_ExitCamera(self.hCam)
#         if not self.camera_initialized:
#             self.camera_initialized = False
            
#     #Save the camera current properties
#     def save_properties(self, folder_path):
#         print("Method not yet implemented for the IDS camera!")
        
#     def get_properties(self, ret=False):
#         print("Method not yet implemented for the IDS camera!")

###############################################################################
#                                                                             #
#                            OBS cam                                          #
#                                                                             #
###############################################################################

class ObsCam():
    
    def __init__(self):
        self.camera_index=0
        self.cap=None
        self.cam_ready=False
        
        self.possible_params=["camera_index"]
        
        self.default_params={"camera_index":0}
        
        self.current_params=self.default_params
        
        self.set_properties(self.current_params)
        
    def get_camera_ready(self):
        if self.cam_ready==False:
            self.cap=cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            self.cam_ready=True
        else:
            print("Camera is already armed")
            
    def get_image(self):
        ret, im_rgb = self.cap.read()
        if ret:
            img=(0.2126*np.array(im_rgb[:,:,0]) + 
                 0.7156*np.array(im_rgb[:,:,1]) + 
                 0.0722*np.array(im_rgb[:,:,2]))
            
            img=np.rint(img/np.max(img)*255)
            img[np.where(img>255)]=255
            
            return img
        
        else:
            print("Image failed to be retrieved. Trying again..")
            
            
    def set_properties(self, properties):
        self.params_to_update={}
        for key in self.possible_params:
            if key in properties.keys():
                self.params_to_update[key]=properties[key]
            else:
                self.params_to_update[key]=self.current_params[key]
        
        self.current_params["camera_index"]=self.params_to_update["camera_index"]
        
    def get_camera_properties(self, ret=False):
        print("--------------------------------------------------------------------------")
        print("camera_index: {}".format(self.current_params["camera_index"]))
        print("--------------------------------------------------------------------------")
    
    def stop_camera(self):
        if self.cam_ready==False:
            print("The camera was already released")
        else:
            self.cap.release()
            self.cam_ready=False
        
    def close(self):
        pass
    

if __name__ == "__main__":

    import matplotlib.pyplot as plt

    test_cam =  IdsCam(1)

    test_cam.get_camera_ready()

    test = test_cam.get_image()

    plt.figure()
    plt.imshow(test)
    plt.show()
    print(test)



    # # camera_controllers.py

    # """
    # Description: This script is used to control the cameras in the experiment.
    # Author: Tiago D. Ferreira, Nuno A. Silva
    # Date Created: 23/02/2022
    # Python Version: 3.8.13
    # """

    # import numpy as np
    # import time
    # import cv2
    # import ctypes

    # # TODO add the doctrings to all the methods and classes
    # # TODO correct all the types in the methods
    # # FIXME add the missiing methods on all the camera objects just for clarity


    # class CameraController():

    #     def __init__(self, camera_name, camera_index=0):
        
    #         self.ready=False  #handle to know if the camera is armed
        
    #         if camera_name == 'Thorlabs':
    #             self.camera = ThorCam(camera_index)
            
    #         elif camera_name == 'OBS':
    #             self.camera = ObsCam()
            
    #         elif camera_name == "XIMEA":
    #             self.camera = XimeaCam() #THE MODULE THAT WE HAVE TO DEVELOP
            
    #         elif camera_name == "IDS":
    #             self.camera = IdsCam(camera_index)
            
                    
    #     #All the cameras have to have the following functions

    #     #Arm the camera
    #     def get_camera_ready(self):
    #         self.camera.get_camera_ready()
    #         self.ready=True
        
    #     #Get a frame or a the average of a number of frames (the number of frames is specified in the properties)
    #     def get_image(self) -> np.ndarray:
    #         return self.camera.get_image()

    #     #Set the camera properties. The propesties should be a dictionary
    #     def set_properties(self, properties):
    #         return self.camera.set_properties(properties)

    #     #Save the camera current properties
    #     def save_properties(self, folder_path):
    #         self.camera.save_properties(folder_path)
        
    #     def get_properties(self,ret=False):
    #         return self.camera.get_camera_properties(ret=ret)

    #     #Disarm the camera, but the camera object continues open
    #     def stop_camera(self):
    #         self.camera.stop_camera()
    #         self.ready=False
        
    #     #Closes the camera
    #     def close(self):
    #         return self.camera.close()


    # ###############################################################################
    # #                                                                             #
    # #                            Thor cam                                         #
    # #                                                                             #
    # ###############################################################################


    # class ThorCam():

    #     def __init__(self, camera_index=0):
        
    #         try:
    #             # if on Windows, use the provided setup script to add the 
    #             #DLLs folder to the PATH
    #             from windows_setup import configure_path
    #             configure_path()
    #         except ImportError:
    #             configure_path = None

    #         from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, OPERATION_MODE

    #         #help(OPERATION_MODE)
        
    #         self.sdk = TLCameraSDK()
    #         available_cameras = self.sdk.discover_available_cameras()
    #         if len(available_cameras) < 1:
    #             print("No cameras detected")
    #         else:
    #             if camera_index == 0:
    #                 self.camera = self.sdk.open_camera(available_cameras[0])
    #             else:
    #                 if str(camera_index) in available_cameras:
    #                     self.camera = self.sdk.open_camera(str(camera_index))
    #                 else:
    #                     print("Invalid index")
        
    #         self.num_frames = 1
        
    #         self.camera_initialized = False
        
        
    #         self.camera_default_configuration = {'operation_mode':0, 
    #                                              'sensor_type':0,
    #                                              'exposure':40, 
    #                                              'image_poll_timeout_ms':20000, 
    #                                              'num_frames':1, 
    #                                              'frames_per_trigger_zero_for_unlimited':1,
    #                                              'binx':1,'biny':1, 
    #                                              'black_level':0,
    #                                              'gain':0,
    #                                              'Default_ROI':True}
            
    #         self.set_properties(self.camera_default_configuration)
                
    #     def set_properties(self, properties):

        
    #         if 'operation_mode' in properties:
    #             #0 SOFTWARE_TRIGGER
    #             self.camera.operation_mode = properties['operation_mode']
        
    #         if 'sensor_type' in properties:
    #             self.camera.sensor_type = properties['sensor_type']
            
    #         if 'ROI' in properties:
    #             self.camera.roi = self.camera.roi._replace(
    #             upper_left_x_pixels = properties['ROI']['upper_left_x_pixels'])
    #             self.camera.roi = self.camera.roi._replace(
    #             upper_left_y_pixels = properties['ROI']['upper_left_y_pixels'])
    #             self.camera.roi = self.camera.roi._replace(
    #             lower_right_x_pixels = properties['ROI']['lower_right_x_pixels'])
    #             self.camera.roi = self.camera.roi._replace(
    #             lower_right_y_pixels = properties['ROI']['lower_right_y_pixels'])
            
        
    #         if 'exposure' in properties:
    #             exposure_min = self.camera.exposure_time_range_us.min
    #             exposure_max = self.camera.exposure_time_range_us.max
            
    #             if int(properties['exposure']) < exposure_min:
    #                 print("WARNING: The minimum exposure value allowed by the camera is " + str(exposure_min) + ".")
    #                 self.camera.exposure_time_us = exposure_min
                
    #             elif int(properties['exposure']) > exposure_max:
    #                 print("WARNING: The maximum exposure value allowed by the camera is " + str(exposure_max) + ".")
    #                 self.camera.exposure_time_us = exposure_max
                
    #             else:
    #                 self.camera.exposure_time_us = int(properties['exposure'])
        
    #         if "image_poll_timeout_ms" in properties:
    #             self.camera.image_poll_timeout_ms = properties['image_poll_timeout_ms']
                
    #         if 'binx' in properties: 
    #             self.camera.binx = properties['binx']
            
    #         if 'biny' in properties: 
    #             self.camera.biny = properties['biny']
            
    #         if 'black_level' in properties:
    #             black_level_min = self.camera.black_level_range.min
    #             black_level_max = self.camera.black_level_range.max
            
    #             if properties['black_level'] < black_level_min:
    #                 print("WARNING: The minimum black level value allowed by the camera is " + str(black_level_min) + ".")
    #                 self.camera.black_level = black_level_min
                
    #             elif properties['black_level'] > black_level_max:
    #                 print("WARNING: The maximum black level value allowed by the camera is " + str(black_level_max) + ".")
    #                 self.camera.black_level = black_level_max
                
    #             else:
    #                 self.camera.black_level = properties['black_level']
                
    #         if 'gain' in properties:
    #             gain_level_min = self.camera.gain_range.min
    #             gain_level_max = self.camera.gain_range.max
            
    #             if properties['gain'] < gain_level_min:
    #                 print("WARNING: The minimum gain level value allowed by the camera is " + str(gain_level_min) + ".")
    #                 self.camera.gain = gain_level_min
                
    #             elif properties['gain'] > gain_level_max:
    #                 print("WARNING: The maximum gain level value allowed by the camera is " + str(gain_level_max) + ".")
    #                 self.camera.gain = gain_level_max
                
    #             else:
    #                 self.camera.gain = properties['gain']

    #         if not self.camera_initialized:
    #             if 'frames_per_trigger_zero_for_unlimited' in properties:
    #                 self.camera.frames_per_trigger_zero_for_unlimited = properties['frames_per_trigger_zero_for_unlimited']
                
    #                 if ('num_frames' in properties) and (properties['frames_per_trigger_zero_for_unlimited'] > 0): 
    #                     self.num_frames = properties['frames_per_trigger_zero_for_unlimited']
    #                 else:
    #                     self.num_frames = properties['num_frames']
                    
    #         if 'Default_ROI' in properties:
    #             if properties['Default_ROI']==True:
    #                 self.set_default_roi()

    #     def set_default_roi(self):
    #         ROI_dic = { "upper_left_x_pixels": 0, 
    #                     "upper_left_y_pixels": 0,
    #                     "lower_right_x_pixels": 1440 - 1, 
    #                     "lower_right_y_pixels": 1080 - 1
    #                    }
        
    #         self.set_properties({'ROI':ROI_dic})
        
    #     def get_camera_properties(self, ret=False):
    #         print("\n")
    #         print("Camera porperties:")
    #         print("Bith depth:", self.camera.bit_depth)
    #         print("Operation mode:", self.camera.operation_mode)
    #         print("Sensor type:", self.camera.sensor_type)
    #         print("Exposure(us):", self.camera.exposure_time_us)
    #         print("Black level:", self.camera.black_level)
    #         print("Frames per trigger:", self.camera.frames_per_trigger_zero_for_unlimited)
    #         print("Number of frames:", self.num_frames)
    #         print("Gain:", self.camera.gain)
    #         print("(binx,biny):", "(" + str(self.camera.binx) + ", " + str(self.camera.biny) + ")")
    #         print("Image shape(pixels):", "(Height:" + str(self.camera.image_height_pixels) + ", Width:" + str(self.camera.image_width_pixels) + ")")
    #         print(self.camera.roi)
    #         print("Image poll timeout(ms):", self.camera.image_poll_timeout_ms)
    #         print("\n")
        
    #         if ret:
    #             pass
        
    #     def save_properties(self, folder_path):
        
    #         properties_string = ""
    #         properties_string += "Camera properties:\n\n"
        
    #         properties_string += "Bith depth : " + str(self.camera.bit_depth)
        
    #         properties_string += "\n"
    #         properties_string += "Operation mode : "
    #         properties_string += str(self.camera.operation_mode)
        
    #         properties_string += "\n"
    #         properties_string += "Sensor type : " + str(self.camera.sensor_type)
        
    #         properties_string += "\n"
    #         properties_string += "Exposure(us) : " 
    #         properties_string += str(self.camera.exposure_time_us)
        
    #         properties_string += "\n"
    #         properties_string +="Black level : " + str(self.camera.black_level)
        
    #         properties_string += "\n"
    #         if self.camera.frames_per_trigger_zero_for_unlimited==0:
    #             properties_string +="Frames per trigger: Continuous mode" 
    #         else:
    #             properties_string += "Frames per trigger : " 
    #             properties_string += str(self.camera.frames_per_trigger_zero_for_unlimited)
        
    #         properties_string += "\n"
    #         properties_string +="Number of frames : " + str(self.num_frames)
        
    #         properties_string += "\n"
    #         properties_string +="Gain : " + str(self.camera.gain)
        
    #         properties_string += "\n"
    #         properties_string += "binx, biny : " + "(" + str(self.camera.binx) 
    #         properties_string += ", " + str(self.camera.biny) + ")"
        
    #         properties_string += "\n"
    #         properties_string += "Image shape(pixels) : Height=" 
    #         properties_string += str(self.camera.image_height_pixels) + ", Width=" 
    #         properties_string += str(self.camera.image_width_pixels)
        
    #         properties_string += "\n"
    #         properties_string += str(self.camera.roi)
        
    #         properties_string += "\n"
    #         properties_string += "Image poll timeout(ms) : " 
    #         properties_string += str(self.camera.image_poll_timeout_ms)
        
        
    #         properties_string += "\n\nData and time:\n"
        
    #         tm = time.localtime()
    #         data_str = str(tm.tm_mday) + "\\" 
    #         data_str += str(tm.tm_mon) + "\\" + str(tm.tm_year)
    #         time_str = str(tm.tm_hour) + ":" + str(tm.tm_min)
        
    #         properties_string += data_str
    #         properties_string += "\n"
    #         properties_string += time_str
        
        
        
    #         path_to_file = folder_path + "\\camera_properties.txt"
        
    #         file_object = open(path_to_file, "w")
        
    #         file_object.write(properties_string)
        
    #         file_object.close()
        
    #     def get_camera_ready(self):
    #         self.camera.arm(self.num_frames)
    #         self.camera_initialized = True

    #     def get_image(self):
        
    #         image_data = []
    #         self.camera.issue_software_trigger()
    #         for i in range(self.num_frames):
            
    #             frame = self.camera.get_pending_frame_or_null()
    #             if frame is not None:

    #                 frame.image_buffer  # .../ perform operations using the data from image_buffer
    #                 image_buffer_copy = np.copy(frame.image_buffer)
    #                 image_data.append(image_buffer_copy)
    #                 #print(np.shape(image_buffer_copy))
    #                 #print(image_buffer_copy.dtype)
    #             else:
    #                 print("timeout reached during polling, program exiting...")
    #                 self.camera.disarm()
    #                 break
        
    #         return np.mean(np.array(image_data),axis=0)/1023

    #     def stop_camera(self):
    #         self.camera.disarm()
    #         self.camera_initialized = False

    #     def close(self):
    #         try:
    #             self.camera.disarm()
    #         except self.camera.TLCameraError as e:
    #             print("TLCameraError: The camera was not armed")
    #         self.camera.dispose()
    #         self.sdk.dispose()
        
        
    # ###############################################################################
    # #                                                                             #
    # #                            Ximea cam                                        #
    # #                                                                             #
    # ###############################################################################
        
    # class XimeaCam():
    #     """
    #     Ximea camera MQ013MG-ON module. Serial number 42650150.

    #     Updatable parameters:

    #     -> exposure: controls single frame exposure time. Set in us. Defaults to 1000us. int;
    #     -> acq_timing_mode: controls the aquisition timing mode. str
    #     Defaults to XI_ACQ_TIMING_MODE_FREE_RUN.
    #     XI_ACQ_TIMING_MODE_FREE_RUN: camera acquires images at a maximum possible framerate
    #     XI_ACQ_TIMING_MODE_FRAME_RATE: Selects a mode when sensor frame acquisition frequency is set to parameter FRAMERATE
    #     XI_ACQ_TIMING_MODE_FRAME_RATE_LIMIT: Selects a mode when sensor frame acquisition frequency is limited by parameter FRAMERATE

    #     -> framerate: if the acquisition timing mode is set to other than FREE_RUN, the the framerate is set. int;
    #     -> gain: Sets the gain of every channel on the camera, set in dB. Actual gain is defined by the closest value
    #     permited by the hardware. Defaults to 0. float.

    #     -> imgdataformat: sets the image format that the came acquires. Possible values:
    #     XI_MONO8
    #     XI_MONO16
    #     XI_RGB24
    #     XI_RGB32
    #     XI_RGB_PLANAR
    #     XI_RAW8
    #     XI_RAW16
    #     XI_FRM_TRANSPORT_DATA
    #     XI_RGB48
    #     XI_RGB64
    #     XI_RGB16_PLANAR
    #     XI_RAW8x2
    #     XI_RAW8x4
    #     XI_RAW16x2
    #     XI_RAW16x4
    #     XI_RAW32
    #     XI_RAW32FLOAT

    #     Altering the image format will alter the numpy data from .get_image() method.
    #     Defaults to XI_MONO8

    #     ->n_frames: number of frames to take. int 
    #     ->trigger_source: Defines source of trigger. Default XI_TRG_OFF. str
    #     XI_TRG_OFF: Capture of next image is automatically started after previous.
    #     XI_TRG_EDGE_RISING: Capture is started on rising edge of selected input.
    #     XI_TRG_EDGE_FALLING: Capture is started on falling edge of selected input
    #     XI_TRG_SOFTWARE: Capture is started with software trigger.
    #     XI_TRG_LEVEL_HIGH: Specifies that the trigger is considered valid as long as the level of the source signal is high.
    #     XI_TRG_LEVEL_LOW: Specifies that the trigger is considered valid as long as the level of the source signal is low.

    #     ->trigger_selector: This parameter selects the type of trigger. Default to XI_TRG_SEL_FRAME_START.
    #     XI_TRG_SEL_FRAME_START: Trigger starts the capture of one frame
    #     XI_TRG_SEL_EXPOSURE_ACTIVE: Trigger controls the start and length of the exposure.
    #     XI_TRG_SEL_FRAME_BURST_START: Trigger starts the capture of the bursts of frames in an acquisition.
    #     XI_TRG_SEL_FRAME_BURST_ACTIVE: Trigger controls the duration of the capture of the bursts of frames in an acquisition.
    #     XI_TRG_SEL_MULTIPLE_EXPOSURES: Trigger which when first trigger starts exposure and consequent pulses are gating exposure(active HI)
    #     XI_TRG_SEL_EXPOSURE_START: Trigger controls the start of the exposure of one Frame.
    #     XI_TRG_SEL_MULTI_SLOPE_PHASE_CHANGE: Trigger controls the multi slope phase in one Frame (phase0 -> phase1) or (phase1 -> phase2).
    #     XI_TRG_SEL_ACQUISITION_START: Trigger starts acquisition of first frame.


    #     ->image_width: sets the image width that the camera will return. Defaults to 1280. The number must be 
    #     equal to image_width=minimum+N*image_width_increment. image_width_increment is set to 16;

    #     ->image_height: sets the image height that the camera will return. Defaults to 1280. The number must be 
    #     equal to image_width=minimum+N*image_height_increment. image_height_increment is set to 2;

    #     ->image_offsetX: sets the image offset from origin in the X direction. image_width+image_offsetX must be lower than the
    #     maximum width (1280). If the value given is not a multiple of the width increment allowed, it is set to the 
    #     nearest lower integer permitted;

    #     ->image_offsetY: sets the image offset from origin in the Y direction. image_height+image_offsetY must be lower than the
    #     maximum width (1024). If the value given is not a multiple of the height increment allowed, it is set to the 
    #     nearest lower integer permitted;

    #     -downsample_mode: defines how we can downsample the output image.
    #     This model doesn't implement binning, but it does skipping. Possible values:
    #     XI_DWN_1x1
    #     XI_DWN_2x2

    #     """

    #     def __init__(self):
    #         from ximea import xiapi
        
    #         self.cam=xiapi.Camera()
    #         self.cam.open_device()
        
    #         self.cam.set_downsampling_type("XI_SKIPPING")
    #         self.cam.enable_recent_frame() #Guarantee that the camera gives the most recent frame
        
        
    #         self.img=xiapi.Image()
    #         self.img_width_increment=self.cam.get_width_increment()
    #         self.img_height_increment=self.cam.get_height_increment()
        
        
        
    #         self.possible_params=["exposure",
    #                               "acq_timing_mode",
    #                               "framerate",
    #                               "gain",
    #                               "imgdataformat",
    #                               "n_frames",
    #                              "trigger_source",
    #                              "trigger_selector",
    #                              "image_width",
    #                              "image_height",
    #                              "image_offsetX",
    #                              "image_offsetY",
    #                              "downsampling_mode",
    #                              "buffers_queue_size",
    #                              "buffer_policy"]
        
    #         self.default_params={"exposure": 50,
    #                              "acq_timing_mode": "XI_ACQ_TIMING_MODE_FREE_RUN",
    #                              "framerate": 100,
    #                              "gain": 0,
    #                              "imgdataformat":"XI_MONO8",
    #                              "n_frames":1,
    #                              "trigger_source":"XI_TRG_OFF",
    #                              "trigger_selector":"XI_TRG_SEL_FRAME_START",
    #                              "image_width":self.cam.get_width_maximum(),
    #                              "image_height":self.cam.get_height_maximum(),
    #                              "image_offsetX":0,
    #                              "image_offsetY":0,
    #                              "downsampling_mode":"XI_DWN_1x1",
    #                              "buffers_queue_size":self.cam.get_buffers_queue_size_minimum(),
    #                              "buffer_policy":"XI_BP_UNSAFE"}
        
        
    #         self.current_params=self.default_params
    #         self.set_properties(self.current_params)
        
    #     def set_properties(self, properties):

    #         self.params_to_update={}
    #         for key in self.possible_params:
    #             if key in properties.keys():
    #                 self.params_to_update[key]=properties[key]
    #             else:
    #                 self.params_to_update[key]=self.current_params[key]
        
    #         ########Test for params to be within permitted ranges###########
    #         ## Exposure
    #         if self.params_to_update["exposure"]<self.cam.get_exposure_minimum():
    #             print("WARNING: exposure value below permitted one. Setting it to minimum.")
    #             self.params_to_update["exposure"] = self.cam.get_exposure_minimum()
    #         elif self.params_to_update["exposure"]>self.cam.get_exposure_maximum():
    #             print("WARNING: exposure value above permitted one. Setting it to maximum.")
    #             self.params_to_update["exposure"] = self.cam.get_exposure_maximum()
        
            
    #         #gain
    #         if self.params_to_update["gain"]<self.cam.get_gain_minimum():
    #             print("WARNING: gain value below permitted one. Setting it to minimum.")
    #             self.params_to_update["gain"] = self.cam.get_gain_minimum()
    #         elif self.params_to_update["gain"]>self.cam.get_gain_maximum():
    #             print("WARNING: gain value above permitted one. Setting it to maximum.")
    #             self.params_to_update["gain"] = self.cam.get_gain_maximum()
        
    #         #width and X offset
    #         tmp_N_width=int((self.params_to_update["image_width"]-self.cam.get_width_minimum())/self.img_width_increment)
    #         tmp_N_offsetX=int(self.params_to_update["image_offsetX"]/self.img_width_increment)
        
    #         self.params_to_update["image_width"]=self.cam.get_width_minimum()+tmp_N_width*self.img_width_increment
    #         self.params_to_update["image_offsetX"]=tmp_N_offsetX*self.img_width_increment
        
    #         if self.params_to_update["image_width"]+self.params_to_update["image_offsetX"]>self.cam.get_width_maximum():
    #             print("WARNING: width value and offset above permitted one. Setting it to default.")
    #             self.params_to_update["image_width"] = self.default_params["image_width"]
    #             self.params_to_update["image_offsetX"] = self.default_params["image_offsetX"]
            
    #         #height and Y offset
    #         tmp_N_height=int((self.params_to_update["image_height"]-self.cam.get_height_minimum())/self.img_height_increment)
    #         tmp_N_offsetY=int(self.params_to_update["image_offsetY"]/self.img_height_increment)
        
    #         self.params_to_update["image_height"]=self.cam.get_height_minimum()+tmp_N_height*self.img_height_increment
    #         self.params_to_update["image_offsetY"]=tmp_N_offsetY*self.img_width_increment
        
    #         if self.params_to_update["image_height"]+self.params_to_update["image_offsetY"]>self.cam.get_height_maximum():
    #             print("WARNING: height value and Y offset above permitted one. Setting it to default.")
    #             self.params_to_update["image_height"] = self.default_params["image_height"]
    #             self.params_to_update["image_offsetY"] = self.default_params["image_offsetY"]
            
    #         #setting parameters
    #         self.cam.set_exposure(self.params_to_update["exposure"])
    #         self.cam.set_acq_timing_mode(self.params_to_update["acq_timing_mode"])
        
    #         if self.params_to_update["acq_timing_mode"]=="XI_ACQ_TIMING_MODE_FREE_RUN":
    #             pass
    #         else:
    #             self.cam.set_framerate(self.params_to_update["framerate"])
        
    #         #framerate
    #         if self.params_to_update["acq_timing_mode"]=="XI_ACQ_TIMING_MODE_FREE_RUN":
    #             pass
    #         else:
    #             if self.params_to_update["framerate"]<self.cam.get_framerate_minimum():
    #                 print("WARNING: framerate value below permitted one. Setting it to minimum.")
    #                 self.params_to_update["framerate"] = self.cam.get_framerate_minimum()
    #             elif self.params_to_update["framerate"]>self.cam.get_framerate_maximum():
    #                 print("WARNING: framerate value above permitted one. Setting it to maximum.")
    #                 self.params_to_update["framerate"] = self.cam.get_framerate_maximum()
                
    #         self.cam.set_gain(self.params_to_update["gain"])
    #         self.cam.set_imgdataformat(self.params_to_update["imgdataformat"])
    #         self.cam.set_trigger_source(self.params_to_update["trigger_source"])
    #         self.cam.set_trigger_selector(self.params_to_update["trigger_selector"])
    #         self.cam.set_width(self.params_to_update["image_width"])
    #         self.cam.set_height(self.params_to_update["image_height"])
    #         self.cam.set_offsetX(self.params_to_update["image_offsetX"])
    #         self.cam.set_offsetY(self.params_to_update["image_offsetY"])
    #         self.cam.set_downsampling(self.params_to_update["downsampling_mode"])
    #         self.cam.set_buffers_queue_size(self.params_to_update["buffers_queue_size"])
    #         self.cam.set_buffer_policy(self.params_to_update["buffer_policy"])
        
    #         self.current_params["exposure"]=self.cam.get_exposure()
    #         self.current_params["acq_timing_mode"]=self.cam.get_acq_timing_mode()
    #         self.current_params["framerate"]=self.cam.get_framerate()
    #         self.current_params["gain"]=self.cam.get_gain()
    #         self.current_params["imgdataformat"]=self.cam.get_imgdataformat()
    #         self.current_params["n_frames"]=self.params_to_update["n_frames"]
    #         self.current_params["trigger_source"]=self.cam.get_trigger_source()
    #         self.current_params["trigger_selector"]=self.cam.get_trigger_selector()
    #         self.current_params["image_width"]=self.cam.get_width()
    #         self.current_params["image_height"]=self.cam.get_height()
    #         self.current_params["image_offsetX"]=self.cam.get_offsetX()
    #         self.current_params["image_offsetY"]=self.cam.get_offsetY()
    #         self.current_params["downsampling_mode"]=self.cam.get_downsampling()
    #         self.current_params["buffers_queue_size"]=self.cam.get_buffers_queue_size()
    #         self.current_params["buffer_policy"]=self.cam.get_buffer_policy()
        
    #     def set_default_roi(self):
    #         properties={"image_width":self.cam.get_width_maximum(),
    #                     "image_height":self.cam.get_height_maximum(),
    #                     "image_offsetX":0,
    #                     "image_offsetY":0}
    #         self.set_properties(properties)
        
        
    #     def get_camera_properties(self, ret=False):
    #         print("--------------------------------------------------------------------------")
    #         print("exposure: {}us".format(self.current_params["exposure"]))
    #         print("acq_timing_mode: {}".format(self.current_params["acq_timing_mode"]))
    #         print("framerate: {}".format(self.current_params["framerate"]))
    #         print("gain: {}dB".format(self.current_params["gain"]))
    #         print("imgdataformat: {}".format(self.current_params["imgdataformat"]))
    #         print("n_frames: {}".format(self.current_params["n_frames"]))
    #         print("trigger_source: {}".format(self.current_params["trigger_source"]))
    #         print("image_width: {}".format(self.current_params["image_width"]))
    #         print("image_height: {}".format(self.current_params["image_height"]))
    #         print("image_offsetX: {}".format(self.current_params["image_offsetX"]))
    #         print("image_offsetY: {}".format(self.current_params["image_offsetY"]))
    #         print("downsampling_mode: {}".format(self.current_params["downsampling_mode"]))
    #         print("buffers_queue_size: {}".format(self.current_params["buffers_queue_size"]))
    #         print("buffer_policy: {}".format(self.current_params["buffer_policy"]))
    #         print("--------------------------------------------------------------------------")
    #         print(self.cam.is_recent_frame())
        
    #         if ret:
    #             return self.current_params

    #     def save_properties(self, path):
    #         log=open(path+r"\\log.txt", "w")
    #         log.write("Camera name: XIMEA \n")
        
        
        
    #         cam_params=self.current_params
    #         for param in cam_params.keys():
    #             log.write("{} : {} \n".format(param,cam_params[param]))
            
    #         properties_string= "\n\nData and time:\n"
        
    #         tm = time.localtime()
    #         data_str = str(tm.tm_mday) + "\\" 
    #         data_str += str(tm.tm_mon) + "\\" + str(tm.tm_year)
    #         time_str = str(tm.tm_hour) + ":" + str(tm.tm_min)
        
    #         properties_string += data_str
    #         properties_string += "\n"
    #         properties_string += time_str
        
    #         log.write(properties_string)
        
    #         log.close()    
        
    #     def get_camera_ready(self):
    #         self.cam.start_acquisition()
        
    #     def get_image(self):
    #         n_blanck=0
        
    #         if "MONO" not in self.current_params["imgdataformat"]:
    #             images=[]

    #             if self.current_params["trigger_source"]=="XI_TRG_OFF":
    #                 for i in range(self.current_params["n_frames"]+n_blanck):
    #                     self.cam.get_image(self.img)
                    
    #                     images.append(self.img.get_image_data_numpy().astype(float))
    #             elif self.current_params["trigger_source"]=="XI_TRG_SOFTWARE" and self.current_params["trigger_selector"]=="XI_TRG_SEL_FRAME_START":
    #                 for i in range(self.current_params["n_frames"]+n_blanck):
    #                     self.cam.set_trigger_software(1)
    #                     self.cam.get_image(self.img)
    #                     images.append(self.img.get_image_data_numpy().astype(float))
                
    #             images=np.asarray(images)
            
    #             avg_img=np.mean(images[n_blanck:],axis=0)
            
                
    #         else:
    #             images=np.zeros((self.current_params["n_frames"]+n_blanck,self.current_params["image_height"],self.current_params["image_width"]), dtype=int)
            
    #             if self.current_params["trigger_source"]=="XI_TRG_OFF":
    #                 for i in range(self.current_params["n_frames"]+n_blanck):
    #                    self.cam.get_image(self.img)
    #                    images[i]=self.img.get_image_data_numpy().astype(float)
                    
    #             elif self.current_params["trigger_source"]=="XI_TRG_SOFTWARE" and self.current_params["trigger_selector"]=="XI_TRG_SEL_FRAME_START":
    #                 for i in range(self.current_params["n_frames"]+n_blanck):
    #                     self.cam.set_trigger_software(1)
    #                     self.cam.get_image(self.img)
                    
    #                     images[i]=self.img.get_image_data_numpy().astype(float)
                    
    #             avg_img=np.mean(images[n_blanck:],axis=0)
            
    #             if self.current_params["imgdataformat"]=="XI_MONO8":
    #                 avg_img=avg_img/(2**8-1)
    #             elif self.current_params["imgdataformat"]=="XI_MONO16":
    #                 avg_img=avg_img/(2**10-1)
                
    #         return avg_img

    #     def stop_camera(self):
    #         self.cam.stop_acquisition()
        
    #     def close(self):
    #         self.cam.close_device()
    #         self.cam=None
        
        
    # ###############################################################################
    # #                                                                             #
    # #                            IDS cam                                          #
    # #                                                                             #
    # ###############################################################################

    # class IdsCamOld():

    #     from pyueye import ueye


    #     _is_SetExposureTime = ueye._bind("is_SetExposureTime",
    #                                      [ueye.ctypes.c_uint, ueye.ctypes.c_double,
    #                                       ueye.ctypes.POINTER(ueye.ctypes.c_double)], ueye.ctypes.c_int)
    #     IS_GET_EXPOSURE_TIME = 0x8000

    #     @staticmethod
    #     def is_SetExposureTime(hCam, EXP, newEXP):
    #         """
    #         Description

    #         The function is_SetExposureTime() sets the with EXP indicated exposure time in ms. Since this
    #         is adjustable only in multiples of the time, a line needs, the actually used time can deviate from
    #         the desired value.

    #         The actual duration adjusted after the call of this function is readout with the parameter newEXP.
    #         By changing the window size or the readout timing (pixel clock) the exposure time set before is changed also.
    #         Therefore is_SetExposureTime() must be called again thereafter.

    #         Exposure-time interacting functions:
    #             - is_SetImageSize()
    #             - is_SetPixelClock()
    #             - is_SetFrameRate() (only if the new image time will be shorter than the exposure time)

    #         Which minimum and maximum values are possible and the dependence of the individual
    #         sensors is explained in detail in the description to the uEye timing.

    #         Depending on the time of the change of the exposure time this affects only with the recording of
    #         the next image.

    #         :param hCam: c_uint (aka c-type: HIDS)
    #         :param EXP: c_double (aka c-type: DOUBLE) - New desired exposure-time.
    #         :param newEXP: c_double (aka c-type: double *) - Actual exposure time.
    #         :returns: IS_SUCCESS, IS_NO_SUCCESS

    #         Notes for EXP values:

    #         - IS_GET_EXPOSURE_TIME Returns the actual exposure-time through parameter newEXP.
    #         - If EXP = 0.0 is passed, an exposure time of (1/frame rate) is used.
    #         - IS_GET_DEFAULT_EXPOSURE Returns the default exposure time newEXP Actual exposure time
    #         - IS_SET_ENABLE_AUTO_SHUTTER : activates the AutoExposure functionality.
    #           Setting a value will deactivate the functionality.
    #           (see also 4.86 is_SetAutoParameter).
            
    #           method adapted from: https://stackoverflow.com/questions/68239400/ids-cameras-pyueye-python-package-set-exposure-parameter-is-setautoparameter-f
    #         """
    #         _hCam = ueye._value_cast(hCam, ueye.ctypes.c_uint)
    #         _EXP = ueye._value_cast(EXP, ueye.ctypes.c_double)
    #         ret = IdsCam._is_SetExposureTime(_hCam, _EXP, ueye.ctypes.byref(newEXP) if newEXP is not None else None)
    #         return ret



    #     def __init__(self, camera_index=0):
        
    #         self.camera_index = camera_index
    #         self.hCam = self.ueye.HIDS(self.camera_index)  # 0: first available camera;  1-254: The camera with the specified camera ID
    #         self.sInfo = self.ueye.SENSORINFO()
    #         self.cInfo = self.ueye.CAMINFO()
    #         self.pcImageMemory = self.ueye.c_mem_p()
    #         self.MemID = self.ueye.int()
    #         self.rectAOI = self.ueye.IS_RECT()
    #         self.pitch = self.ueye.INT()
    #         self.nBitsPerPixel = self.ueye.INT(10)  # 24: bits per pixel for color mode; take 8 bits per pixel for monochrome
    #         self.channels = 1  # 3: channels for color mode(RGB); take 1 channel for monochromeq
    #         self.m_nColorMode = self.ueye.INT()  # Y8/RGB16/RGB24/REG32
    #         self.bytes_per_pixel = int(self.nBitsPerPixel / 8)
    #         self.refPt = [(0,1),(2,3)]
        





    #         # Starts the driver and establishes the connection to the camera
    #         nRet = self.ueye.is_InitCamera(self.hCam, None)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_InitCamera ERROR")

    #         # Reads out the data hard-coded in the non-volatile camera memory and writes it to the data structure that cInfo points to
    #         nRet = self.ueye.is_GetCameraInfo(self.hCam, self.cInfo)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_GetCameraInfo ERROR")

    #         # You can query additional information about the sensor type used in the camera
    #         nRet = self.ueye.is_GetSensorInfo(self.hCam, self.sInfo)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_GetSensorInfo ERROR")

    #         nRet = self.ueye.is_ResetToDefault(self.hCam)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_ResetToDefault ERROR")

    #         # Set display mode to DIB
    #         nRet = self.ueye.is_SetDisplayMode(self.hCam, self.ueye.IS_SET_DM_DIB)

    #         self.m_nColorMode = self.ueye.IS_CM_MONO8
    #         self.nBitsPerPixel = self.ueye.INT(8)
    #         self.bytes_per_pixel = int(self.nBitsPerPixel / 8)

    #         # Can be used to set the size and position of an "area of interest"(AOI) within an image
    #         nRet = self.ueye.is_AOI(self.hCam, self.ueye.IS_AOI_IMAGE_GET_AOI, self.rectAOI, self.ueye.sizeof(self.rectAOI))
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_AOI ERROR")

    #         self.width = self.rectAOI.s32Width
    #         self.height = self.rectAOI.s32Height

    #         self.camera_initialized = True
                


    #     def set_camera_exposure(self, level_us):
    #         """
    #         :param level_us: exposure level in micro-seconds, or zero for auto exposure
        
    #         note that you can never exceed 1000000/fps, but it is possible to change the fps
    #         """
    #         p1 = self.ueye.DOUBLE()
    #         if level_us == 0:
    #             rc = IdsCam._is_SetExposureTime(self.hCam, self.ueye.IS_SET_ENABLE_AUTO_SHUTTER, p1)
    #             print(f'set_camera_exposure: set to auto')
    #         else:
    #             ms = self.ueye.DOUBLE(level_us / 1000)
    #             rc = IdsCam._is_SetExposureTime(self.hCam, ms, p1)
    #             print(f'set_camera_exposure: requested {ms.value}, got {p1.value}', end='\r')
            
    #     def set_properties(self, properties):
    #         if 'exposure' in properties:
    #             self.set_camera_exposure(properties['exposure'])

        
    #     def get_camera_ready(self):
    #         # Allocates an image memory for an image having its dimensions defined by width and height and its color depth defined by nBitsPerPixel
    #         nRet = self.ueye.is_AllocImageMem(self.hCam, self.width, self.height, self.nBitsPerPixel, self.pcImageMemory, self.MemID)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_AllocImageMem ERROR")
    #         else:
    #             # Makes the specified image memory the active memory
    #             nRet = self.ueye.is_SetImageMem(self.hCam, self.pcImageMemory, self.MemID)
    #             if nRet != self.ueye.IS_SUCCESS:
    #                 print("is_SetImageMem ERROR")
    #             else:
    #                 # Set the desired color mode
    #                 nRet = self.ueye.is_SetColorMode(self.hCam, self.m_nColorMode)

    #         # Activates the camera's live video mode (free run mode)
    #         nRet = self.ueye.is_CaptureVideo(self.hCam, self.ueye.IS_WAIT)
    #         # nRet = self.ueye.is_Trigger(self.hCam)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             # print("is_CaptureVideo ERROR")
    #             pass

    #         # Enables the queue mode for existing image memory sequences
    #         self.nRet = self.ueye.is_InquireImageMem(self.hCam, self.pcImageMemory, self.MemID, self.width, self.height, self.nBitsPerPixel, self.pitch)
    #         if self.nRet != self.ueye.IS_SUCCESS:
    #             print("is_InquireImageMem ERROR")
    #         else:
    #             #print("Press q to leave the programm")
    #             pass
        
    #         time.sleep(1)
        
    #         #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
    #         #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
    #         #del test_out
        

    #     def get_image(self):
    #         ms = self.ueye.DOUBLE(20)
    #         frame = np.zeros((self.height.value, self.width.value))
    #         nshots = 4
    #         counter = 0
    #         #time.sleep(1)
    #         for i in range(0, nshots):
    #             if self.nRet == self.ueye.IS_SUCCESS:
    #                 array = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
    #                 # frame += np.reshape(array.astype(np.float16), (self.height.value, self.width.value))
    #                 frame = np.reshape(array.astype(np.float32), (self.height.value, self.width.value))
    #                 #print(np.max(array.astype(np.float16)))
    #                 #print("\n")
    #                 counter += 1
    #         counter = 1
    #         return np.array(frame)/counter/255.0

    #     def stop_camera(self):
    #         if not self.camera_initialized:
    #             self.camera_initialized = False

    #     def close(self):
    #         self.ueye.is_ExitCamera(self.hCam)
    #         if not self.camera_initialized:
    #             self.camera_initialized = False
            
    #     #Save the camera current properties
    #     def save_properties(self, folder_path):
    #         print("Method not yet implemented for the IDS camera!")
        
    #     def get_properties(self, ret=False):
    #         print("Method not yet implemented for the IDS camera!")


    # class IdsCam():

    #     from pyueye import ueye



    #     _is_SetExposureTime = ueye._bind("is_SetExposureTime",
    #                                      [ueye.ctypes.c_uint, ueye.ctypes.c_double,
    #                                       ueye.ctypes.POINTER(ueye.ctypes.c_double)], ueye.ctypes.c_int)
    #     IS_GET_EXPOSURE_TIME = 0x8000

    #     @staticmethod
    #     def is_SetExposureTime(hCam, EXP, newEXP):
    #         """
    #         Description

    #         The function is_SetExposureTime() sets the with EXP indicated exposure time in ms. Since this
    #         is adjustable only in multiples of the time, a line needs, the actually used time can deviate from
    #         the desired value.

    #         The actual duration adjusted after the call of this function is readout with the parameter newEXP.
    #         By changing the window size or the readout timing (pixel clock) the exposure time set before is changed also.
    #         Therefore is_SetExposureTime() must be called again thereafter.

    #         Exposure-time interacting functions:
    #             - is_SetImageSize()
    #             - is_SetPixelClock()
    #             - is_SetFrameRate() (only if the new image time will be shorter than the exposure time)

    #         Which minimum and maximum values are possible and the dependence of the individual
    #         sensors is explained in detail in the description to the uEye timing.

    #         Depending on the time of the change of the exposure time this affects only with the recording of
    #         the next image.

    #         :param hCam: c_uint (aka c-type: HIDS)
    #         :param EXP: c_double (aka c-type: DOUBLE) - New desired exposure-time.
    #         :param newEXP: c_double (aka c-type: double *) - Actual exposure time.
    #         :returns: IS_SUCCESS, IS_NO_SUCCESS

    #         Notes for EXP values:

    #         - IS_GET_EXPOSURE_TIME Returns the actual exposure-time through parameter newEXP.
    #         - If EXP = 0.0 is passed, an exposure time of (1/frame rate) is used.
    #         - IS_GET_DEFAULT_EXPOSURE Returns the default exposure time newEXP Actual exposure time
    #         - IS_SET_ENABLE_AUTO_SHUTTER : activates the AutoExposure functionality.
    #           Setting a value will deactivate the functionality.
    #           (see also 4.86 is_SetAutoParameter).
            
    #           method adapted from: https://stackoverflow.com/questions/68239400/ids-cameras-pyueye-python-package-set-exposure-parameter-is-setautoparameter-f
    #         """
    #         _hCam = ueye._value_cast(hCam, ueye.ctypes.c_uint)
    #         _EXP = ueye._value_cast(EXP, ueye.ctypes.c_double)
    #         ret = IdsCam._is_SetExposureTime(_hCam, _EXP, ueye.ctypes.byref(newEXP) if newEXP is not None else None)
    #         return ret



    #     def __init__(self, camera_index=0):
        
    #         self.camera_index = camera_index
    #         self.hCam = self.ueye.HIDS(self.camera_index)  # 0: first available camera;  1-254: The camera with the specified camera ID
    #         self.sInfo = self.ueye.SENSORINFO()
    #         self.cInfo = self.ueye.CAMINFO()
    #         self.pcImageMemory = self.ueye.c_mem_p()
    #         self.MemID = self.ueye.int()
    #         self.rectAOI = self.ueye.IS_RECT()
    #         self.pitch = self.ueye.INT()
    #         self.nBitsPerPixel = self.ueye.INT(10)  # 24: bits per pixel for color mode; take 8 bits per pixel for monochrome
    #         self.channels = 1  # 3: channels for color mode(RGB); take 1 channel for monochromeq
    #         self.m_nColorMode = self.ueye.INT()  # Y8/RGB16/RGB24/REG32
    #         self.bytes_per_pixel = int(self.nBitsPerPixel / 8)
    #         self.refPt = [(0,1),(2,3)]
    #         self.nShutterMode = self.ueye.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START
        
    #         self.ueye.is_DeviceFeature(self.hCam, 
    #                                    self.ueye.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START,
    #                                    pParam=self.nShutterMode,
    #                                    cbSizeOfParam=self.ueye.sizeof(self.nShutterMode))
        

    #         self.ImageData: np.ndarray



    #         # Starts the driver and establishes the connection to the camera
    #         nRet = self.ueye.is_InitCamera(self.hCam, None)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_InitCamera ERROR")

    #         # Reads out the data hard-coded in the non-volatile camera memory and writes it to the data structure that cInfo points to
    #         nRet = self.ueye.is_GetCameraInfo(self.hCam, self.cInfo)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_GetCameraInfo ERROR")

    #         # You can query additional information about the sensor type used in the camera
    #         nRet = self.ueye.is_GetSensorInfo(self.hCam, self.sInfo)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_GetSensorInfo ERROR")

    #         nRet = self.ueye.is_ResetToDefault(self.hCam)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_ResetToDefault ERROR")

    #         # Set display mode to DIB
    #         nRet = self.ueye.is_SetDisplayMode(self.hCam, self.ueye.IS_SET_DM_DIB)

    #         self.m_nColorMode = self.ueye.IS_CM_MONO8
    #         self.nBitsPerPixel = self.ueye.INT(8)
    #         self.bytes_per_pixel = int(self.nBitsPerPixel / 8)

    #         # Can be used to set the size and position of an "area of interest"(AOI) within an image
    #         nRet = self.ueye.is_AOI(self.hCam, self.ueye.IS_AOI_IMAGE_GET_AOI, self.rectAOI, self.ueye.sizeof(self.rectAOI))
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_AOI ERROR")

    #         self.width = self.rectAOI.s32Width
    #         self.height = self.rectAOI.s32Height

    #         self.camera_initialized = True
                
    # #     def set_properties(self, properties):

        
    # #         if 'operation_mode' in properties:
    # #             #0 SOFTWARE_TRIGGER
    # #             self.camera.operation_mode = properties['operation_mode']
        
    # #         if 'sensor_type' in properties:
    # #             self.camera.sensor_type = properties['sensor_type']
            
    # #         if 'ROI' in properties:
    # #             self.camera.roi = self.camera.roi._replace(
    # #             upper_left_x_pixels = properties['ROI']['upper_left_x_pixels'])
    # #             self.camera.roi = self.camera.roi._replace(
    # #             upper_left_y_pixels = properties['ROI']['upper_left_y_pixels'])
    # #             self.camera.roi = self.camera.roi._replace(
    # #             lower_right_x_pixels = properties['ROI']['lower_right_x_pixels'])
    # #             self.camera.roi = self.camera.roi._replace(
    # #             lower_right_y_pixels = properties['ROI']['lower_right_y_pixels'])

    #     def set_camera_exposure(self, level_us):
    #         """
    #         :param level_us: exposure level in micro-seconds, or zero for auto exposure
        
    #         note that you can never exceed 1000000/fps, but it is possible to change the fps
    #         """
    #         p1 = self.ueye.DOUBLE()
    #         if level_us == 0:
    #             rc = IdsCam._is_SetExposureTime(self.hCam, self.ueye.IS_SET_ENABLE_AUTO_SHUTTER, p1)
    #             print(f'set_camera_exposure: set to auto')
    #         else:
    #             ms = self.ueye.DOUBLE(level_us / 1000)
    #             rc = IdsCam._is_SetExposureTime(self.hCam, ms, p1)
    #             print(f'set_camera_exposure: requested {ms.value}, got {p1.value}', end='\r')

    #             self.ueye.is_DeviceFeature(self.hCam, 
    #                                    self.ueye.IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START,
    #                                    pParam=self.nShutterMode,
    #                                    cbSizeOfParam=self.ueye.sizeof(self.nShutterMode))


    #     def set_properties(self, properties):
    #         if 'exposure' in properties:
    #             self.set_camera_exposure(properties['exposure'])

        
    #     def get_camera_ready(self):
    #         # Allocates an image memory for an image having its dimensions defined by width and height and its color depth defined by nBitsPerPixel
    #         nRet = self.ueye.is_AllocImageMem(self.hCam, self.width, self.height, self.nBitsPerPixel, self.pcImageMemory, self.MemID)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             print("is_AllocImageMem ERROR")
    #         else:
    #             # Makes the specified image memory the active memory
    #             nRet = self.ueye.is_SetImageMem(self.hCam, self.pcImageMemory, self.MemID)
    #             if nRet != self.ueye.IS_SUCCESS:
    #                 print("is_SetImageMem ERROR")
    #             else:
    #                 # Set the desired color mode
    #                 nRet = self.ueye.is_SetColorMode(self.hCam, self.m_nColorMode)

    #         nRet = self.ueye.is_FreezeVideo

    #         # Activates the camera's live video mode (free run mode)
    #         nRet = self.ueye.is_CaptureVideo(self.hCam, self.ueye.IS_WAIT)
    #         # nRet = self.ueye.is_Trigger(self.hCam)
    #         if nRet != self.ueye.IS_SUCCESS:
    #             # print("is_CaptureVideo ERROR")
    #             pass

    #         # Enables the queue mode for existing image memory sequences
    #         self.nRet = self.ueye.is_InquireImageMem(self.hCam, self.pcImageMemory, self.MemID, self.width, self.height, self.nBitsPerPixel, self.pitch)
    #         if self.nRet != self.ueye.IS_SUCCESS:
    #             print("is_InquireImageMem ERROR")
    #         else:
    #             #print("Press q to leave the programm")
    #             pass
        
    #         time.sleep(1)
        
    #         #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
    #         #test_out = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
    #         #del test_out
        

    #     def get_image(self):
    #         ms = self.ueye.DOUBLE(20)
    #         frame = np.zeros((self.height.value, self.width.value))
    #         nshots = 4
    #         counter = 0
    #         #time.sleep(1)
    #         for i in range(0, nshots):
    #             if self.nRet == self.ueye.IS_SUCCESS:
    #                 array = self.ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel, self.pitch, copy=True)
    #                 # frame += np.reshape(array.astype(np.float16), (self.height.value, self.width.value))
    #                 frame = np.reshape(array.astype(np.float32), (self.height.value, self.width.value))
    #                 #print(np.max(array.astype(np.float16)))
    #                 #print("\n")
    #                 counter += 1
    #         counter = 1
    #         return np.array(frame)/counter/255.0

    #     def stop_camera(self):
    #         if not self.camera_initialized:
    #             self.camera_initialized = False

    #     def close(self):
    #         self.ueye.is_ExitCamera(self.hCam)
    #         if not self.camera_initialized:
    #             self.camera_initialized = False
            
    #     #Save the camera current properties
    #     def save_properties(self, folder_path):
    #         print("Method not yet implemented for the IDS camera!")
        
    #     def get_properties(self, ret=False):
    #     print("Method not yet implemented for the IDS camera!")

    # ###############################################################################
    # #                                                                             #
    # #                            OBS cam                                          #
    # #                                                                             #
    # ###############################################################################

    # class ObsCam():

    # def __init__(self):
    #     self.camera_index=0
    #     self.cap=None
    #     self.cam_ready=False

    #     self.possible_params=["camera_index"]

    #     self.default_params={"camera_index":0}

    #     self.current_params=self.default_params

    #     self.set_properties(self.current_params)

    # def get_camera_ready(self):
    #     if self.cam_ready==False:
    #         self.cap=cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
    #         self.cam_ready=True
    #     else:
    #         print("Camera is already armed")
        
    # def get_image(self):
    #     ret, im_rgb = self.cap.read()
    #     if ret:
    #         img=(0.2126*np.array(im_rgb[:,:,0]) + 
    #                 0.7156*np.array(im_rgb[:,:,1]) + 
    #                 0.0722*np.array(im_rgb[:,:,2]))
        
    #         img=np.rint(img/np.max(img)*255)
    #         img[np.where(img>255)]=255
        
    #         return img

    #     else:
    #         print("Image failed to be retrieved. Trying again..")
        
        
    # def set_properties(self, properties):
    #     self.params_to_update={}
    #     for key in self.possible_params:
    #         if key in properties.keys():
    #             self.params_to_update[key]=properties[key]
    #         else:
    #             self.params_to_update[key]=self.current_params[key]

    #     self.current_params["camera_index"]=self.params_to_update["camera_index"]

    # def get_camera_properties(self, ret=False):
    #     print("--------------------------------------------------------------------------")
    #     print("camera_index: {}".format(self.current_params["camera_index"]))
    #     print("--------------------------------------------------------------------------")

    # def stop_camera(self):
    #     if self.cam_ready==False:
    #         print("The camera was already released")
    #     else:
    #         self.cap.release()
    #         self.cam_ready=False

    # def close(self):
    #     pass


    # if __name__ == "__main__":

    # import matplotlib.pyplot as plt

    # test_cam =  IdsCam(1)

    # test_cam.get_camera_ready()

    # test = test_cam.get_image()

    # plt.figure()
    # plt.imshow(test)
    # print(test)
    # plt.show()