import threading


import numpy as np


class CircularBuffer:
    """ A Circular Buffer stores values in a predefined memory space. Once the buffer is full, the oldest values
    will be overwritten.
    """
    def __init__(self, shape, dtype):
        """ Creates a new circular buffer. The shape of the buffer assumes the first dimension will be the length
        of the buffer. The other dimensions should respect what is expected from the data. Dtype is a numpy dtype.
        Both shape and dtype are passed directly to `np.empty`.
        """
        self.buffer = np.empty(shape=shape, dtype=dtype)
        self.curr_index = -1
        self.total_index = -1  # Keeps track of the total number of elements that have ever been stored in the buffer
        self.lock = threading.Lock()

    def append(self, values):
        """ Appends a new set of values to the end of the circular buffer. If values has a dimension less than the dimension
        of the buffer, it is assumed it is a single value.
        """
        with self.lock:
            if len(values.shape) == len(self.buffer.shape) - 1:
                values = values.reshape((1, values.shape))

            for i in range(values.shape[0]):
                if self.curr_index == self.buffer.shape[0]-1:
                    self.curr_index = -1
                self.buffer[self.curr_index+1] = values[i]
                self.curr_index += 1
                self.total_index += 1

    def get_last_N(self, N):
        """ Returns the last N elements of the buffer."""
        if N > self.total_index:
            raise ValueError("There are not enough values in the buffer")
        if N > self.length:
            raise ValueError("There are not enough values in the buffer")
        with self.lock:
            i = self.curr_index
            if i < self.length:
                return self.buffer[i+1-N:i+1]
            else:
                return np.concatenate((self.buffer[-(N-i-1):], self.buffer[:i+1]), axis=0)

    def get_values(self, i, j):
        """ Returns the slice of values between i and j. They are relative to the absolute counter in the buffer
        """
        relative_i = self.total_index - i
        relative_j = self.total_index - j
        if relative_i > self.length or relative_j > self.length:
            raise BufferError(f"Data is not available anymore {i}, {j}")

        if i<j:
            last_val = relative_j
        else:
            last_val = relative_i
        total_values = abs(i - j)

        if self.curr_index - last_val > 0:
            if total_values < last_val:
                return self.buffer[last_val-total_values:last_val]
            else:
                return np.concatenate((self.buffer[:last_val], self.buffer[-(total_values-last_val):]), axis=0)
        else:
            return np.concatenate((self.buffer[-last_val:], self.buffer[:abs(last_val-total_values)]), axis=0)


    @property
    def length(self):
        return self.buffer.shape[0]

    def __len__(self):
        return self.length


if __name__ == "__main__":
    buffer = CircularBuffer(shape=(500, 120, 120), dtype=np.uint8)
    data = np.random.randint(0, 255, size=(500, 120, 120), dtype=np.uint8)
    buffer.append(data)
    print(buffer.get_last_N(33).shape)
    # Process(target=calculate_fft, args=buffer.get_last_N(33)) # TODO: This can be a speed bottleneck.
    #  Sending arrays to a different process may need to serialize the array, and this will be slow
    data = np.random.randint(0, 255, size=(75, 120, 120), dtype=np.uint8)
    buffer.append(data)
    print(buffer.length)
    print(buffer.total_index)
    print(buffer.get_values(510, 550).shape)
