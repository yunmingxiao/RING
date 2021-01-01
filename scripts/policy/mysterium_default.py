import datetime
import time

# Use global variables to store neccessary states across function calls
bwlimit_time_ratio = 0

def bandwidth_policy(now, month_start, next_month, 
                     data_plan, used_data, 
                     curr_bandwidth_limit, bandwidth_history):
    """
    The policy for setting the bandwidth limit

    Parameters
    ----------
    now : float
        Current timestamp (in seconds).
    month_start : float
        The timestamp at the beginning of the current month (in seconds).
    next_month : float
        The timestamp at the beginning of next month (in seconds).
    data_plan : float
        The data cap for the current month (in bytes).
    used_data : float
        The data have used in the current month (in bytes).
    curr_bandwidth_limit : float
        The current bandwidth limit (in Mbps)
    bandwidth_history : list [{'time': float, 'Bps': float}]
        The used bandwidth for the past N minues, N is the length of the list

    """
    left_data = (data_plan - used_data) * 8 # bytes to bits
    time_left = next_month - now
    new_ratio = curr_bandwidth_limit \
                / (60*8*sum([bh['Bps'] for bh in bandwidth_history])) \
                / (len(bandwidth_history)*60)

    global bwlimit_time_ratio
    if bwlimit_time_ratio <= 0:
        # initialized the bandwidth-time-ratio 
        bwlimit_time_ratio = new_ratio
    # update the ratio
    bwlimit_time_ratio = 0.5 * new_ratio + 0.5 * bwlimit_time_ratio
    
    new_limit = curr_bandwidth_limit * left_data / time_left / bwlimit_time_ratio
    return new_limit

def price_policy(month_start, now, next_month,
                 data_plan, used_data, 
                 current_price, prices_in_network):
    """
    The policy for setting the bandwidth limit

    Parameters
    ----------
    now : float
        Current timestamp (in seconds).
    month_start : float
        The timestamp at the beginning of the current month (in seconds).
    next_month : float
        The timestamp at the beginning of next month (in seconds).
    data_plan : float
        The data cap for the current month (in Gigabytes).
    used_data : float
        The data have used in the current month (in Gigabytes).
    current_price : float
        The current service price
    prices_in_network : json
        The service prices of other dVPN nodes in the network

    """
    return prices_in_network