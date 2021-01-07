import datetime
import time
import statistics

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
    left_time = next_month - now
    if left_time <= 0:
        return curr_bandwidth_limit
    used_data_last = 60 * 8 * sum([bh['Bps'] for bh in bandwidth_history])
    used_time_last = 60 * len(bandwidth_history)

    if (used_time_last == 0 or used_data_last == 0):
        # no historical data, just keep the current settings
        new_ratio = left_data / left_time
    else:
        new_ratio = used_data_last / used_time_last

    global bwlimit_time_ratio
    if bwlimit_time_ratio <= 0:
        # initialized the bandwidth-time-ratio 
        bwlimit_time_ratio = new_ratio
    # update the ratio
    bwlimit_time_ratio = 0.5 * new_ratio + 0.5 * bwlimit_time_ratio
    
    new_limit = curr_bandwidth_limit * left_data / left_time / bwlimit_time_ratio

    # set the max and min threshold
    if new_limit > 3200:
        new_limit = 3200
    elif new_limit < 0.01:
        new_limit = 0.01
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
        Note: sometimes the field "price_per_min" is not present
        [{"account_addr": str, "location": {"country": "US"}, "price_per_GB": float, "price_per_min": float, ...}, ...]
    """
    prices_per_gb = [p['price_per_GB'] for p in prices_in_network]
    prices_per_min = [p['price_per_min'] for p in prices_in_network]
    return [statistics.median(prices_per_gb), statistics.median(prices_per_min)]