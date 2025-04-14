import FileContext from "./FileContext";
import React,{ useState } from "react";
const FileState =(props)=>{
    const[data,datachange]=useState({});
    
    return(
        <FileContext.Provider value={{data,datachange}}>
            {props.children}
        </FileContext.Provider>
    )
}

export default FileState;