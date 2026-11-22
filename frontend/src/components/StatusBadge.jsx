import React, {useState,useEffect,useRef} from 'react'
function Pill({children,tone='muted'}){return <span className={'pill pill-'+tone}>{children}</span>}
function Status({value}){return <Pill tone={value==='completed'?'green':value==='available'?'lime':value==='accepted'?'blue':value==='picked_up'?'orange':value==='pending'?'orange':value==='declined'?'red':'muted'}><i className="status-dot"/>{cap(value)}</Pill>}
import {cap} from '../utils/formatters'
export {Pill,Status}
