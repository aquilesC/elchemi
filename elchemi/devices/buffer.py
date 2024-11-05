from queue import Queue
from numpy import array, sum, stack
from sys import getsizeof
import h5py
from elchemi import buffer_folder
from threading import Condition, Event

class Buffer:
    def __init__(self, type, size = 1, dtype = None, name = 'Buffer'):
        self.type = type
        self.d_type = dtype
        self.pixel_fmt = None
        self.size = size
        self.buffer = None
        self.name = name
        self.frame_rates = []
        self.pause_storage = Event()

        # Defines buffers
        if self.type == 'Queue':
            self.buffer = Queue(maxsize=self.size)
        elif self.type == 'List':
            self.buffer = []


    def put(self, img_arr):  
        """ Put an array into the ring buffer
        Parameters
        ----------
        img_arr

        Returns
        -------

        """
        if self.type == 'Queue':
            if self.buffer.full():
                self.buffer.get()
            self.buffer.put(img_arr)
        elif self.type == 'List':
            self.buffer.append(img_arr)
    
    def get(self):
        if self.type == 'Queue':
            return self.buffer.get()
        elif self.type == 'List':
            return self.buffer[1]
    
    def get_buffer(self):
        #with self.buffer_condition:
        if self.type == 'Queue':
            return self.buffer
        elif self.type == 'List':
            return array(self.buffer)

    def get_size(self):
        ''' For each type of buffer used, this returns the space on the disk it will take.
        For queue queues: Calculate the size of each element in buffer and sum. 
        For list queues: The expression sys.getsizeof(arr) + arr.nbytes calculates the total size for each array in the list.
        '''
        if self.type == 'Queue':
            total_s = 0    
            for arr in self.buffer.queue:
                if isinstance(arr, array):
                    s = array.nbytes
                else:
                    s = getsizeof(arr)
                total_s += s
            return total_s
        elif self.type == 'List':
            print(sum(getsizeof(arr) + arr.nbytes for arr in self.buffer))
            return sum(getsizeof(arr) + arr.nbytes for arr in self.buffer)
    
    def to_array(self):
        pass

    def __len__(self):
        if self.type == 'Queue':
            return self.buffer.qsize()
        else:
            return len(self.buffer)
        
    def get_dtype(self):
        if "Bayer" in self.pixel_fmt:
            if self.pixel_fmt.endswith('8'):
                self.d_type = 'np.uint8'
            elif self.pixel_fmt.endswith('10'):        
                self.d_type = 'np.uint32'
            elif self.pixel_fmt.endswith('32'):
                self.d_type = 'np.uint16'
            elif self.pixel_fmt.endswith('16'):
                self.buffer.dtype = 'np.uint16'
        # !!! to complete with other dtypes


    def save(self):
        ''' Saves buffer into H5 file'''
        if self.type == 'Queue':
            data = []
            while not self.buffer.empty():
                data.append(self.buffer.get())
            arr = stack(data, axis = 0)
        else:
            arr = self.buffer
        with h5py.File('data.h5', 'w') as hf:
            hf.create_dataset(str(self.get_size), data=arr)
