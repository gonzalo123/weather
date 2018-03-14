#!/usr/bin/env node
noble = require('noble');

var status = false;
var address = process.argv[2];

if (!address) {
    console.log('Usage "./reader.py <sensor mac address>"');
    process.exit();
}

function hexToInt(hex) {
    var num, maxVal;
    if (hex.length % 2 !== 0) {
        hex = "0" + hex;
    }
    num = parseInt(hex, 16);
    maxVal = Math.pow(2, hex.length / 2 * 8);
    if (num > maxVal / 2 - 1) {
        num = num - maxVal;
    }

    return num;
}

noble.on('stateChange', function(state) {
    status = (state === 'poweredOn');
});

noble.on('discover', function(peripheral) {
    if (peripheral.address == address) {
        var data = peripheral.advertisement.manufacturerData.toString('hex');
        out = {
            temperature: parseFloat(hexToInt(data.substr(10, 2)+data.substr(8, 2))/10).toFixed(1),
            humidity: Math.min(100,parseInt(data.substr(14, 2),16))
        };
        console.log(JSON.stringify(out))
        noble.stopScanning();
        process.exit();
    }
});

noble.on('scanStop', function() {
    noble.stopScanning();
});

setTimeout(function() {
    noble.stopScanning();
    noble.startScanning();
}, 2000);


setTimeout(function() {
    noble.stopScanning();
    process.exit()
}, 20000);