from gglsbl import SafeBrowsingList
import Constants #dvpn.result_processing.Constants

sbl = SafeBrowsingList(Constants.gsbk, 'gsb_v4.db')
sbl.update_hash_prefix_cache()