import FileContext from "./FileContext";
import React,{ useEffect, useState } from "react";
const FileState =(props)=>{
    const[data,datachange]=useState({});
    const [val,setval]=useState({});
    useEffect(()=>{
      if(Object.keys(data).length !== 0){
        if (data?.file_info.validation_results) {
            const grouped = {};
      
            data.file_info.validation_results.forEach((item) => {
              const col = item.Column;
              if (!grouped[col]) {
                grouped[col] = [];
              }
              grouped[col].push(item);
            });
      
            setval(grouped);
            console.log(grouped);
          }
        }
    },[data])
    
    return(
        <FileContext.Provider value={{data,datachange,val}}>
            {props.children}
        </FileContext.Provider>
    )
}

export default FileState;