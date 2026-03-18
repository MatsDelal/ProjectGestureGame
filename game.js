// ==========================================
// 1. GAME VARIABLES & STATE
// ==========================================
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

let WIDTH = window.innerWidth;
let HEIGHT = window.innerHeight;
canvas.width = WIDTH;
canvas.height = HEIGHT;

window.addEventListener('resize', () => {
    WIDTH = window.innerWidth;
    HEIGHT = window.innerHeight;
    canvas.width = WIDTH;
    canvas.height = HEIGHT;
    // Recalculate player ground position on resize
    updatePlayerGround();
});

let state = "START"; // START, PLAYING, GAMEOVER
let score = 0;
let highScore = 0;
let globalSpeed = 10;
let spawnTimer = 0;

let bgScroll = 0;
let groundScroll = 0;

// Hand tracking state
let wasFist = false;
let isFist = false;

// UI Elements
const uiLayer = document.getElementById('ui-layer');
const startBtn = document.getElementById('start-btn');
const subTitle = document.getElementById('sub-title');

// ==========================================
// 2. LOAD ASSETS
// ==========================================
const images = {
    bg: new Image(),
    ground: new Image(),
    obstacle: new Image(),
    bat: new Image(),
    playerStatic: new Image()
};

images.bg.src = 'images/background.png';
images.ground.src = 'images/ground.png';
images.obstacle.src = 'images/obstacle.png';
images.bat.src = 'images/bat.png';
images.playerStatic.src = 'images/player1.png';

// Load the 50 run frames dynamically
const runFrames = [];
for (let i = 0; i < 50; i++) {
    const img = new Image();
    // Format number to 3 digits (000 - 049)
    const numStr = i.toString().padStart(3, '0');
    // Using a try-catch pattern isn't easy with image src, we'll assume they exist
    // from the Python version.
    img.src = `images/run/running_${numStr}.png`;
    runFrames.push(img);
}

const sounds = {
    jump: new Audio('sounds/jump.wav'),
    gameover: new Audio('sounds/gameover.wav'),
    bgMusic: new Audio('sounds/cave_theme.mp3')
};
sounds.bgMusic.loop = true;

// ==========================================
// 3. GAME CLASSES
// ==========================================
let playerGroundY = 0;

function updatePlayerGround() {
    const groundVisualHeight = 240;
    const playerHeight = 250;
    const playerOffset = 60;
    playerGroundY = HEIGHT - groundVisualHeight - playerHeight + playerOffset;
}
updatePlayerGround();

class Player {
    constructor() {
        this.width = 250;
        this.height = 250;
        this.x = WIDTH / 3;
        this.y = playerGroundY;
        this.velY = 0;
        this.gravity = 1.2;
        this.jumpPower = -22;
        this.animTick = 0;
    }

    jump() {
        if (this.y === playerGroundY) {
            this.velY = this.jumpPower;
            sounds.jump.currentTime = 0;
            sounds.jump.play().catch(e => console.warn("Audio play failed:", e));
        }
    }

    update() {
        this.velY += this.gravity;
        this.y += this.velY;

        if (this.y >= playerGroundY) {
            this.y = playerGroundY;
            this.velY = 0;
            this.animTick++;
        }
    }

    draw(ctx) {
        let currentImg = null;

        if (this.y === playerGroundY && runFrames.length > 0 && runFrames[0].complete) {
            // Animate running
            const frameIdx = Math.floor(this.animTick / 2) % runFrames.length;
            currentImg = runFrames[frameIdx];
        } else if (this.y < playerGroundY && runFrames.length > 0 && runFrames[0].complete) {
            // Jumping frame
            currentImg = runFrames[Math.floor(runFrames.length / 2)];
        } else if (images.playerStatic.complete) {
            currentImg = images.playerStatic;
        }

        if (currentImg && currentImg.complete && currentImg.naturalWidth > 0) {
            ctx.drawImage(currentImg, this.x, this.y, this.width, this.height);
        } else {
            // Fallback rectangle
            ctx.fillStyle = '#4ade80';
            ctx.fillRect(this.x, this.y, this.width, this.height);
        }
    }
    
    getHitbox() {
        // Inflated hitbox (made smaller for fairness like in Python)
        return {
            x: this.x + 50,
            y: this.y + 40,
            width: this.width - 100,
            height: this.height - 80
        };
    }
}

class Obstacle {
    constructor(speed) {
        this.width = 100;
        this.height = 100;
        this.x = WIDTH + 50;
        this.speed = speed;
        
        const groundVisualHeight = 240;
        const obstacleOffset = 40;
        this.y = HEIGHT - groundVisualHeight - this.height + obstacleOffset;
        this.isBat = false;
    }

    update() {
        this.x -= this.speed;
    }

    draw(ctx) {
        if (images.obstacle.complete && images.obstacle.naturalWidth > 0) {
            ctx.drawImage(images.obstacle, this.x, this.y, this.width, this.height);
        } else {
            ctx.fillStyle = '#ff4d4d';
            ctx.beginPath();
            ctx.moveTo(this.x, this.y + this.height);
            ctx.lineTo(this.x + this.width / 2, this.y);
            ctx.lineTo(this.x + this.width, this.y + this.height);
            ctx.fill();
        }
    }
    
    getHitbox() {
        return {
            x: this.x + 10,
            y: this.y + 10,
            width: this.width - 20,
            height: this.height - 20
        };
    }
}

class FlyingBat extends Obstacle {
    constructor(speed) {
        super(speed);
        this.width = 120;
        this.height = 100;
        this.isBat = true;
        this.speed = speed + 2;
        this.animTick = 0;
        
        // Calculate running player head height
        const groundVisualHeight = 240;
        const playerRunningY = HEIGHT - groundVisualHeight - 250 + 60;
        this.y = playerRunningY - this.height + 40;
    }

    update() {
        this.x -= this.speed;
        this.animTick++;
    }

    draw(ctx) {
        const hover = Math.sin(this.animTick * 0.1) * 15;
        const drawY = this.y + hover;
        
        if (images.bat.complete && images.bat.naturalWidth > 0) {
            ctx.drawImage(images.bat, this.x, drawY, this.width, this.height);
        } else {
            ctx.fillStyle = '#333';
            ctx.fillRect(this.x, drawY, this.width, this.height);
        }
    }
    
    getHitbox() {
        const hover = Math.sin(this.animTick * 0.1) * 15;
        return {
            x: this.x + 20,
            y: this.y + hover + 20,
            width: this.width - 40,
            height: this.height - 40
        };
    }
}

let player = new Player();
let obstacles = [];

function resetGame() {
    score = 0;
    globalSpeed = 10;
    spawnTimer = 0;
    obstacles = [];
    player = new Player();
    bgScroll = 0;
    groundScroll = 0;
    
    // Reset and play music
    sounds.bgMusic.currentTime = 0;
    sounds.bgMusic.play().catch(e => console.warn("Background music failed to play:", e));
}

// ==========================================
// 4. DRAWING & RENDERING
// ==========================================
function checkCollision(rect1, rect2) {
    return (
        rect1.x < rect2.x + rect2.width &&
        rect1.x + rect1.width > rect2.x &&
        rect1.y < rect2.y + rect2.height &&
        rect1.y + rect1.height > rect2.y
    );
}

function drawBackground() {
    // Parallax background
    if (images.bg.complete && images.bg.naturalWidth > 0) {
        if (state === "PLAYING") {
            bgScroll -= globalSpeed * 0.2;
            if (bgScroll <= -WIDTH) bgScroll += WIDTH;
        }
        ctx.drawImage(images.bg, bgScroll, 0, WIDTH, HEIGHT);
        ctx.drawImage(images.bg, bgScroll + WIDTH, 0, WIDTH, HEIGHT);
    } else {
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
    }

    // Ground layer
    const groundH = 240;
    if (images.ground.complete && images.ground.naturalWidth > 0) {
        if (state === "PLAYING") {
            groundScroll -= globalSpeed;
            if (groundScroll <= -WIDTH) groundScroll += WIDTH;
        }
        ctx.drawImage(images.ground, groundScroll, HEIGHT - groundH, WIDTH, groundH);
        ctx.drawImage(images.ground, groundScroll + WIDTH, HEIGHT - groundH, WIDTH, groundH);
    } else {
        ctx.fillStyle = '#333';
        ctx.fillRect(0, HEIGHT - groundH, WIDTH, groundH);
    }
}

function gameLoop() {
    // 1. Logic Update
    if (state === "PLAYING") {
        player.update();

        // Spawn logic
        spawnTimer--;
        if (spawnTimer <= 0) {
            if (score > 200 && Math.random() < 0.3) {
                obstacles.push(new FlyingBat(globalSpeed));
            } else {
                obstacles.push(new Obstacle(globalSpeed));
            }
            const minTimer = Math.max(40, 100 - Math.floor(score/10));
            const maxTimer = Math.max(60, 150 - Math.floor(score/10));
            spawnTimer = Math.floor(Math.random() * (maxTimer - minTimer + 1)) + minTimer;
        }

        // Update and check collisions
        const pHitbox = player.getHitbox();
        
        for (let i = obstacles.length - 1; i >= 0; i--) {
            let obs = obstacles[i];
            obs.update();
            
            if (checkCollision(pHitbox, obs.getHitbox())) {
                state = "GAMEOVER";
                sounds.bgMusic.pause();
                sounds.gameover.play().catch(e=>e);
                if (score > highScore) highScore = score;
            }
            
            // Remove off-screen
            if (obs.x + obs.width < 0) {
                obstacles.splice(i, 1);
            }
        }
        
        score++;
        if (score % 300 === 0) globalSpeed++;
    }

    // 2. Render
    ctx.clearRect(0, 0, WIDTH, HEIGHT);
    drawBackground();

    if (state === "PLAYING" || state === "GAMEOVER") {
        player.draw(ctx);
        obstacles.forEach(o => o.draw(ctx));

        // Score Text
        ctx.fillStyle = 'white';
        ctx.font = '30px Arial';
        ctx.fillText(`Score: ${score}  (Record: ${highScore})`, 20, 40);
    }

    if (state === "START") {
        // Draw some semi-transparent overlay just for aesthetics if wanted
    }

    if (state === "GAMEOVER") {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
        ctx.fillStyle = '#ff4d4d';
        ctx.font = '60px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('GAME OVER', WIDTH/2, HEIGHT/2);
        ctx.fillStyle = 'white';
        ctx.font = '30px Arial';
        ctx.fillText('Make a FIST to restart!', WIDTH/2, HEIGHT/2 + 50);
        ctx.textAlign = 'left'; // reset
    }

    requestAnimationFrame(gameLoop);
}

// ==========================================
// 5. MEDIAPIPE WEB INTEGRATION
// ==========================================
import { FilesetResolver, GestureRecognizer } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3";

const video = document.getElementById("webcam");

let gestureRecognizer;

async function initMediaPipe() {
    try {
        const vision = await FilesetResolver.forVisionTasks(
            "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
        );
        gestureRecognizer = await GestureRecognizer.createFromOptions(vision, {
            baseOptions: {
                modelAssetPath: "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task",
                delegate: "GPU"
            },
            runningMode: "VIDEO",
            numHands: 1
        });
        
        // Show start button
        subTitle.innerText = "Ready!";
        startBtn.style.display = "block";
    } catch (e) {
        console.error("Failed to load MediaPipe:", e);
        subTitle.innerText = "Failed to load AI Models.";
    }
}

// Start Camera when User Clicks (browsers require user interaction for cam/audio)
startBtn.addEventListener("click", async () => {
    // 1. "Unlock" all audio for mobile/strict browser policies
    Object.values(sounds).forEach(audio => {
        audio.play().then(() => {
            audio.pause();
            audio.currentTime = 0;
        }).catch(e => console.warn("Audio unlock failed for:", audio.src, e));
    });

    // Request Camera
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        video.addEventListener("loadeddata", predictWebcam);
        
        uiLayer.style.display = "none";
        
        // 2. Start Background Music immediately on user interaction
        sounds.bgMusic.play().catch(e => console.warn("Initial music play failed:", e));

        // Start drawing frame-loop
        requestAnimationFrame(gameLoop);
    } catch(err) {
        alert("Camera access denied or unavailable.");
    }
});

let lastVideoTime = -1;
async function predictWebcam() {
    if (video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime;
        
        if (gestureRecognizer) {
            const results = gestureRecognizer.recognizeForVideo(video, Date.now());
            
            if (results.gestures.length > 0) {
                const categoryName = results.gestures[0][0].categoryName;
                const scoreConf = results.gestures[0][0].score;
                
                // Closed_Fist is the MediaPipe default category for fist
                if (categoryName === "Closed_Fist" && scoreConf > 0.6) {
                    isFist = true;
                } else {
                    isFist = false;
                }
            } else {
                isFist = false;
            }
            
            // Apply gesture logic
            if (isFist && !wasFist) {
                if (state === "PLAYING") {
                    player.jump();
                } else if (state === "START" || state === "GAMEOVER") {
                    resetGame();
                    state = "PLAYING";
                }
            }
            wasFist = isFist;
        }
    }
    
    // Check next frame
    requestAnimationFrame(predictWebcam);
}

// Boot up sequence
initMediaPipe();
