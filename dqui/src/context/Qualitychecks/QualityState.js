import QualityContext from "./QualityContext";
import React,{ useState } from "react";
const QualityState =(props)=>{

    const ruleids = {"not_null":2,"contains":10,"range":13,"min":16,"max":17,"set_contain":7};
      
    
    
    return(
        <QualityContext.Provider value={{ruleids}}>
            {props.children}
        </QualityContext.Provider>
    )
}

export default QualityState;