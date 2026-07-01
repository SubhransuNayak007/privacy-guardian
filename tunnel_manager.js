const { spawn, execSync } = require('child_process');
const https = require('https');

const TUNNEL_URL = 'https://sweet-shirts-sneeze.loca.lt';
const PORT = 8000;

let tunnelProcess = null;
let consecutiveFailures = 0;

function startTunnel() {
    console.log(`Starting localtunnel on port ${PORT}...`);
    // Kill any existing localtunnel processes first just in case
    try {
        execSync('taskkill /f /im node.exe /fi "COMMANDLINE eq *localtunnel*" >nul 2>&1');
    } catch (e) {
        // Ignore
    }

    tunnelProcess = spawn('npx.cmd', ['localtunnel', '--port', PORT.toString(), '--subdomain', 'sweet-shirts-sneeze'], {
        stdio: 'pipe',
        windowsHide: true,
        shell: true
    });

    tunnelProcess.stdout.on('data', (data) => {
        console.log(`[LT] ${data.toString().trim()}`);
    });

    tunnelProcess.stderr.on('data', (data) => {
        console.error(`[LT ERROR] ${data.toString().trim()}`);
    });

    tunnelProcess.on('close', (code) => {
        console.log(`[LT] Process exited with code ${code}`);
        tunnelProcess = null;
    });
}

function checkTunnel() {
    return new Promise((resolve) => {
        const req = https.get(TUNNEL_URL, {
            headers: { 'Bypass-Tunnel-Reminder': 'true' },
            timeout: 10000
        }, (res) => {
            if (res.statusCode === 503 || res.statusCode === 504) {
                resolve(false);
            } else {
                resolve(true);
            }
        });

        req.on('error', () => {
            resolve(false);
        });

        req.on('timeout', () => {
            req.destroy();
            resolve(false);
        });
    });
}

async function monitor() {
    if (!tunnelProcess || tunnelProcess.killed) {
        startTunnel();
        await new Promise(r => setTimeout(r, 5000)); // Wait for it to start
        return;
    }

    const isUp = await checkTunnel();
    if (isUp) {
        consecutiveFailures = 0;
    } else {
        consecutiveFailures++;
        console.log(`Tunnel check failed (${consecutiveFailures}/3)`);
    }

    if (consecutiveFailures >= 3) {
        console.log('Tunnel appears dead. Restarting...');
        if (tunnelProcess) {
            try {
                execSync(`taskkill /f /t /pid ${tunnelProcess.pid} >nul 2>&1`);
            } catch (e) {
                tunnelProcess.kill('SIGKILL');
            }
        }
        consecutiveFailures = 0;
        startTunnel();
        await new Promise(r => setTimeout(r, 5000));
    }
}

// Initial start
startTunnel();

// Check every 15 seconds
setInterval(monitor, 15000);

process.on('SIGINT', () => {
    if (tunnelProcess) {
        try {
            execSync(`taskkill /f /t /pid ${tunnelProcess.pid} >nul 2>&1`);
        } catch (e) {
            tunnelProcess.kill('SIGKILL');
        }
    }
    process.exit(0);
});
