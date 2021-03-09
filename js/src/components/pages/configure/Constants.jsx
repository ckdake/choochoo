import React, {useEffect, useState} from 'react';
import {ConfirmedWriteButton, Layout} from "../../elements";
import {ColumnCard, ColumnList, Loading, TextCard} from "../../../common/elements";
import {csrfFetch, handleJson} from "../../functions";
import {Grid, Paper, TextField} from "@material-ui/core";
import {FMT_DAY_TIME} from "../../../constants";
import format from 'date-fns/format';
import {makeStyles} from "@material-ui/core/styles";
import {DateTimePicker} from "@material-ui/pickers";


const useStyles = makeStyles(theme => ({
    paper: {
        padding: theme.spacing(1),
    },
    delete: {
        marginBottom: theme.spacing(1),
    },
}));


function isString(value) {
    return value instanceof String || typeof (value) === typeof ('string')
}


function isNumber(value) {
    return !isNaN(value);
}


function isComposite(value) {
    return !(isString(value) || isNumber(value));
}


const EDIT_WIDTH = 10;
const BTN_WIDTH = 2;


function Field(props) {
    const {label, value, setValue} = props;
    return (<TextField label={label} value={value} onChange={event => setValue(event.target.value)} fullWidth/>);
}


function Value(props) {

    const {constantState, index = 0} = props;
    const [constant, setConstant] = constantState;
    const value = constant.values[index].value;

    if (constant.composite) {
        return Object.keys(value).map((name, i) => (
            <Field label={name} value={value[name]}
                   setValue={value => {
                       const copy = {...constant};
                       copy.values[index].value[name] = value;
                       setConstant(copy);
                   }} key={i}/>));
    } else {
        return (<Field label='Value' value={value}
                       setValue={value => {
                           const copy = {...constant};
                           copy.values[index].value = value;
                           setConstant(copy);
                       }}/>);
    }
}


function DatedValue(props) {

    const {constantState, index = 0} = props;
    const [constant, setConstant] = constantState;
    const classes = useStyles();

    return (<Grid item xs={EDIT_WIDTH}><Paper variant='outlined' className={classes.paper}>
        <Value constantState={constantState} index={index}/>
        <DateTimePicker value={constant.values[index].time} format={FMT_DAY_TIME}
                        onChange={time => {
                            const copy = {...constant};
                            copy.values[index].time = time;
                            setConstant(copy);
                        }}/>
    </Paper></Grid>);
}


function UndatedValue(props) {

    const {constantState, index = 0} = props;
    const classes = useStyles();

    return (<Grid item xs={EDIT_WIDTH}><Paper variant='outlined' className={classes.paper}>
        <Value constantState={constantState} index={index}/>
    </Paper></Grid>);
}


function emptyCopy(constant) {
    // need to take care here to do deep copy
    const extra = {...constant};
    if (constant.values.length > 0) {
        if (constant.composite) {
            extra.values = [{value: {...constant.values[0].value}, statistic: 0}];
            Object.keys(extra.values[0].value).forEach(
                name => extra.values[0].value[name] = isString(extra.values[0].value[name]) ? '' : 0);
        } else {
            extra.values = [{value: '', statistic: 0}];
        }
    } else {
        extra.values = [{value: '', statistic: 0}];
    }
    extra.values[0].time = format(new Date(), FMT_DAY_TIME);
    return extra;
}


function Description(props) {
    const {constant} = props;
    const unique_id = `description-${constant.name}`;
    setTimeout(() => document.getElementById(unique_id).innerHTML = constant.description);
    return (<Grid item xs={12}>
        <div id={unique_id}/>
    </Grid>);
}


function DatedConstant(props) {

    const {constant, reload} = props;
    const constantState = useState(constant);
    const [newConstant, setNewConstant] = constantState;
    const extraState = useState(emptyCopy(constant));
    const [extra, setExtra] = extraState;

    return (<ColumnCard header={constant.name}>
        <Description constant={constant}/>
        {newConstant.values.map((entry, i) =>
            <DatedValue index={i} constantState={constantState} key={i}/>)}
        <Grid item xs={BTN_WIDTH}>
            <Delete disabled={newConstant !== constant} href='/api/configure/delete-constant'
                    reload={reload} json={constant.name}/>
            <Save disabled={newConstant === constant} href='/api/configure/constant'
                  reload={reload} json={convertTypes(newConstant)}/>
        </Grid>
        <DatedValue constantState={extraState}/>
        <ConfirmedWriteButton xs={BTN_WIDTH} label='Add' disabled={extra.values[0].value === ''}
                              href='/api/configure/constant' setData={reload}
                              json={convertTypes(extra)}>
            Adding a new value for the constant will change how data are processed.
        </ConfirmedWriteButton>
    </ColumnCard>);
}


function Save(props) {
    const {xs=12, disabled=false, href, reload, json} = props;
    return (<ConfirmedWriteButton xs={xs} label='Save' disabled={disabled}
                                  href={href} setData={reload} json={json}>
        Modifying the constant will change how data are processed.
    </ConfirmedWriteButton>);
}

function Delete(props) {
    const {xs=12, href, reload, json} = props;
    const classes = useStyles();
    return (<ConfirmedWriteButton className={classes.delete} xs={xs} label='Delete'
                                  href={href} setData={reload} json={json}>
        Deleting the constant will change how data are processed.
    </ConfirmedWriteButton>);
}


function UndatedConstant(props) {

    const {constant, reload} = props;
    if (constant.values.length === 0) {
        constant.values.push({value: '', time: format(new Date(), FMT_DAY_TIME), statistic: 0});
    }
    const constantState = useState(constant);
    const [newConstant, setNewConstant] = constantState;

    return (<ColumnCard header={constant.name}>
        <Description constant={constant}/>
        <UndatedValue constantState={constantState}/>
        <Grid item xs={BTN_WIDTH}>
            <Delete disabled={newConstant !== constant} href='/api/configure/delete-constant'
                    reload={reload} json={constant.name}/>
            <Save disabled={newConstant === constant} href='/api/configure/constant'
                  reload={reload} json={convertTypes(newConstant)}/>
        </Grid>
    </ColumnCard>);
}


function Columns(props) {

    const {constants, reload} = props;

    if (constants === null) {
        return <Loading/>;
    } else {
        return (<ColumnList>
            <TextCard header='Introduction'>
                <p>Constants are user-defined values that modify processing.</p>
                <p>Despite their name, some constants can be defined for multiple times.
                    The value used for any particular calculation will be the next-earliest value.
                    So, for example, if you defined your FTHR in April, and then again in October,
                    the value from April would be used to calculate fitness and fatigue for May.</p>
                <p>Constants generally define low-level details that you probably don't want to change.&nbsp;
                    <b>Consider them an advanced feature.</b>&nbsp;
                    Future releases will move the more commonly used features to dedicated,
                    easier-to-use, pages.</p>
            </TextCard>
            {constants.map((constant, i) =>
                constant.single ?
                    <UndatedConstant constant={constant} reload={reload} key={i}/> :
                    <DatedConstant constant={constant} reload={reload} key={i}/>)}
        </ColumnList>);
    }
}


function annotateConstants(constants) {
    constants.forEach(constant => {
        constant.composite = constant.values.length > 0 && isComposite(constant.values[0].value);
        if (constant.composite) {
            const value = constant.values[0].value;
            constant.types = {};
            Object.keys(value).forEach(name => constant.types[name] = isString(value[name]) ? String : Number);
        }
    });
    return constants;
}


function convertTypes(constant) {
    if (constant.composite) {
        constant.values.forEach(
            entry => Object.keys(entry.value).forEach(
                name => {
                    entry.value[name] = constant.types[name](entry.value[name])
                }));
    }
    return constant;
}


export default function Constants(props) {

    const {match, history} = props;
    const [constants, setConstants] = useState(null);
    const [edits, setEdits] = useState(0);
    const errorState = useState(null);
    const [error, setError] = errorState;

    function reload() {
        setEdits(edits + 1);
    }

    useEffect(() => {
        setConstants(null);
        csrfFetch('/api/configure/constants')
            .then(handleJson(history, constants => setConstants(annotateConstants(constants)), setError));
    }, [edits]);

    return (
        <Layout title='Edit Constants'
                content={<Columns constants={constants} reload={reload}/>} errorState={errorState}/>
    );
}
