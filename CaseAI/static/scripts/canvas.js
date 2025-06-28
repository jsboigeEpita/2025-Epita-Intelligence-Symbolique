let GAME;

const config = {
    type: Phaser.AUTO,
    parent: 'phaser_container',
    width: 1584,
    height: 1152,
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH,
    },
    physics: {
        default: 'arcade',
        arcade: {
            debug: false,
        }
    },
    scene: {
        preload,
        create,
        update
    }
};

function preload() {
    const index = Math.floor(Math.random(2));
    this.load.image('bg', `static/assets/medieval/smithy/${index}.jpg`)

    for (let i = 1; i <= 12; i++) 
        this.load.image(`girl${i}`, `static/assets/tokens/character/girl${i}.png`)

    for (let i = 1; i <= 23; i++)
        this.load.image(`man${i}`, `static/assets/tokens/character/man${i}.png`)
}

function create() {
    const bg = this.add.image(0, 0, 'bg').setOrigin(0)

    const resizeBg = () => {
        bg.setDisplaySize(this.scale.width, this.scale.height)
    }

    resizeBg()

    this.scale.on('resize', resizeBg)

    this.agents = this.physics.add.group({
        allowGravity: false
    });

    let possibleMans = []
    let possibleGirls = []

    for (let i = 1; i <= 12; i++) possibleGirls.push(`girl${i}`)
    for (let i = 1; i <= 23; i++) possibleMans.push(`man${i}`)

    for (let key in backend.plot.suspects) {
        let suspect = backend.plot.suspects[key]

        let possibleGender = suspect.gender === 'M' ? possibleMans : possibleGirls
        const randomAvatarIndex = Math.floor(Math.random() * possibleGender.length)

        let avatar = possibleGender.splice(randomAvatarIndex, 1)

        let agent = this.physics.add.sprite(
            MAP_INFO.starting_point.x,
            MAP_INFO.starting_point.y,
            avatar
        )

        agent.avatar = avatar
        agent.suspect = suspect

        agent.body.velocity.x = 0;
        agent.body.velocity.y = 0;

        agent.body.setSize(50, 90)

        agent.setScale(0.5)
        agent.setCollideWorldBounds(true);

        agent.setInteractive()

        agent.on('pointerdown', () => {
            setTestimonyAgent(agent)
            playSound(Sounds.HM)
        })

        this.agents.add(agent)

        createPicture(agent)
    }

    this.physics.add.collider(this.agents, this.agents);

    this.obstacles = this.physics.add.staticGroup();

    for (const obstacle of MAP_INFO.obstacles) {
        const obs = this.obstacles.create(obstacle.x, obstacle.y, 'wall')
        obs.setOrigin(0)
        obs.setDisplaySize(obstacle.width, obstacle.height)
        obs.body.setSize(obstacle.width, obstacle.height)
        obs.setVisible(false)

        this.obstacles.add(obs)
    }

    this.physics.add.collider(this.agents, this.obstacles);
}

function update() {
    this.agents.children.iterate(agent => {
        if (!agent) return;

        if (Math.random() < 0.02) {
            agent.body.velocity.x += Phaser.Math.FloatBetween(-50, 50);
            agent.body.velocity.y += Phaser.Math.FloatBetween(-50, 50);

            const maxSpeed = 100;
            const vx = agent.body.velocity.x;
            const vy = agent.body.velocity.y;
            const speed = Math.sqrt(vx * vx + vy * vy);
            if (speed > maxSpeed) {
                agent.body.velocity.x = (vx / speed) * maxSpeed;
                agent.body.velocity.y = (vy / speed) * maxSpeed;
            }
        }
    });
}


function createGame() {
    GAME = new Phaser.Game(config);
}