def remove_detected_windows(time_array, data_array, detected_windows):
    """
    Removes data corresponding to abnormal windows from the time and observation arrays.
    
    Parameters:
        time_array (np.ndarray): Array of time values.
        data_array (np.ndarray): Array of observation values.
        detected_windows (list of tuples): List of abnormal windows, each defined by a tuple (start_index, end_index).
    
    Returns:
        tuple: Filtered time_array and data_array with abnormal data removed.
    """
    if len(time_array) != len(data_array):
        raise ValueError("time_array and data_array must have the same length.")
    
    # Create a mask of valid data points
    valid_mask = np.ones(len(time_array), dtype=bool)
    
    # Mark indices in abnormal windows as invalid
    for start_idx, end_idx in detected_windows:
        valid_mask[start_idx:end_idx + 1] = False
    
    # Apply the mask to both arrays
    filtered_time = time_array[valid_mask]
    filtered_observation = data_array[valid_mask]
    
    return filtered_time, filtered_observation
