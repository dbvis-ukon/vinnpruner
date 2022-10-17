//export const API_ADDRESS = '172.31.0.37';
export const API_ADDRESS = undefined;
export const API_PORT = 5000;
/* API_RELATIVE will append a path if API_ADDRESS is left undefined
   If API_RELATIVE is specified and API_ADDRESS is undefined, API_PORT will be ignored
   Example: API_RELATIVE = "app"
   Output: URL: {$proto}://${hostname}/app
*/
export const API_RELATIVE = "";