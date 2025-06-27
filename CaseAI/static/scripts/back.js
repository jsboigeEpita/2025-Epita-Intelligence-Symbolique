const backend = {
  model: {
    API_KEY: "",
    API_URL: "https://api.openai.com/v1/chat/completions",
    name: "gpt-4o"
  },
  plot: {}, // pseudo internal
  suspects: {
    // "name": {messages: [{}], alibi: str, observations: [str]}
  },
  watson : {
    alibis: [],
    observations: []
  },
  end_speech : null,
  ended : false,
  watson_found : false,
};

// var Logic = require('logic-solver');

// Private func
async function chatAIHistory(messages) {
  const body = {
    model: backend.model.name,
    messages: messages,
    response_format: { type: "json_object" },
  };
  
  try {
    const res = await fetch(backend.model.API_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${backend.model.API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });
    
    const data = await res.json();
    const content = data.choices?.[0]?.message?.content;
    
    if (!content) {
      console.log(data)
      throw new Error("No response from API");
    }
    
    const parsedJSON = JSON.parse(content);
    return parsedJSON;    
  } catch (err) {
    console.error("Error:", err.message);
    throw err;
  }
}

// Private func
async function chatAIPrompt(prompt) {
  return chatAIHistory([{role: "system", content: prompt}]);
}

function formatString(str) {
  return str.toLowerCase().replaceAll(" ", "_");
}

function checkAlibi(plotSuspect, alibi) {
  const regexTest = /I was in (?:the )?(.*?) from */i;
  const regexRef = /in (?:the )?(.*?) from */i;
  
  const test = alibi.match(regexTest);
  const ref = plotSuspect.alibi.match(regexRef);
  if (test && ref)
    return test[1] === ref[1];

  return false;
}

function addWatsonAlibi(p, alibi) {
  const regex = /in (?:the )?(.*?) from */i;
  const match = alibi.match(regex);
  if (match) {
    backend.watson.alibis.push({
      person: formatString(p),
      room: formatString(match[1])
    })
  }
}

function addWatsonObservation(obs) {
  const regex = /Saw (.*?) in (?:the )?(.*?) around */i;
  const match = obs.match(regex);
  if (match) {
    backend.watson.observations.push({
      person: formatString(match[1]),
      room: formatString(match[2])
    })
  }
}

async function ask(question, name) {
  if (!backend.suspects[name]) {
    backend.suspects[name] = {};
    backend.suspects[name].messages = [];
    backend.suspects[name].messages.push({
      role: "system",
      content: createSuspect(backend.plot, name)
    });
  }

  plotSuspect = backend.plot.suspects.find((el) => el.name === name);
  
  backend.suspects[name].messages.push({role: "user", content: question});
  
  const response = await chatAIHistory(backend.suspects[name].messages);
  
  backend.suspects[name].messages.push({role: "assistant", content: response.response});
  
  const mapper = createMapper(plotSuspect.observations, response.response);
  const feats = await chatAIPrompt(mapper);

  // Check again alibi
  feats.alibi |= checkAlibi(plotSuspect, response.response);

  if (feats.alibi) {
    feats.trash = undefined;
    if (!backend.suspects[name].alibi)
      addWatsonAlibi(name, plotSuspect.alibi);
    backend.suspects[name].alibi = plotSuspect.alibi;
  }
  
  obss = []
  for (const i of feats.observations) {
    const obs = plotSuspect.observations[i];

    if (i == 0)
      addWatsonObservation(obs);

    if (!backend.suspects[name].observations)
      backend.suspects[name].observations = [];

    if (!backend.suspects[name].observations.includes(obs)) {
      backend.suspects[name].observations.push(obs);
      obss.push(obs);
    }
  
  }

  // console.log(feats.trash);
  // console.log(await watsonHasFound());

  return {
    alibi: backend.suspects[name].alibi,
    new_obs: obss,
    trash: response.trash,
    response: response.response
  };
};

const rooms = {
  "Shop": ["Storage Room", "Forge", "Bedroom", "Courtyard"],
  "Bedroom": ["Shop", "Courtyard", "Dining Room"],
  "Dining Room": ["Courtyard", "Bedroom"],
  "Courtyard": ["Bedroom", "Shop"],
  "Storage Room": ["Precious Materials Room", "Forge"],
  "Precious Materials Room": ["Storage Room"],
  "Forge": ["Storage Room", "Finishing Workshop", "Foundry"],
  "Finishing Workshop": ["Forge"],
  "Foundry": ["Forge"]
}

const deaths = [
    "burned",
    "strangled",
    "poisoned",
    "stabbed",
    "beheaded",
    "drowned",
    "hanged",
    "bludgeoned",
    "crushed",
    "shot",
    "slit_throat",
    "freezing",
    "tortured",
    "impaled",
    "buried",
    "suffocated",
    "exploded",
    "traped"
]

const murder_motives = [
    "revenge",
    "inheritance",
    "romantic jealousy",
    "money debt",
    "trade rivalry",
    "secret affair",
    "family feud",
    "covering crime",
    "religious conflict",
    "political intrigue",
    "blackmail",
    "theft gone wrong",
    "social status",
    "forged documents",
    "disgrace avoidance",
    "professional jealousy",
    "rejected proposal",
    "superstition",
    "accused of witchcraft",
    "honor defense",
    "betrayal",
    "love rivalry",
    "envy",
    "abuse",
    "silencing witness",
    "guild dispute",
    "nobles secret",
    "favoritism",
    "ritual sacrifice",
    "delusions of prophecy",
    "delayed justice",
    "shameful secret",
    "reputation preservation",
    "paranoia",
    "illegitimate heir"
]

forge_prefessions = [
  "blacksmith",
  "apprentice_blacksmith",
  "armorer",
  "weapon_smith",
]

professions = [
    "blacksmith",
    "apprentice_blacksmith",
    "armorer",
    "weapon_smith",
    "locksmith",
    "carpenter",
    "leatherworker",
    "potter",
    "glassblower",
    "miner",
    "merchant",
    "innkeeper",
    "town_guard",
    "watchman",
    "baker",
    "butcher",
    "farmer",
    "cleric",
    "scribe",
    "doctor",
    "alchemist",
    "schoolmaster",
    "courier",
    "tax_collector",
    "nobleman",
    "servant",
    "beggar",
    "witch_hunter",
    "minstrel",
    "travelling_merchant",
    "herbalist",
    "executioner",
    "falconer",
]

// Private func
function getRandomElements(arr, n) {
  if (n > arr.length)
    throw new Error("Cannot select more elements than are in the array");

  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }

  return shuffled.slice(0, n);
}

// Private func
function randomTime() {
  hour = Math.floor(Math.random() * 24);
  mins = Math.floor(Math.random() * 12) * 5;

  return [hour, mins];
}

// Private func
function addTime(hour, mins, deltaMin) {
  let h = hour;
  let m = mins + deltaMin;
  while (m < 0) {
    h -= 1;
    m = 60 + m;
  }

  while (m >= 60) {
    h += 1;
    m = m - 60;
  }

  if (h >= 24)
    h = h - 24;

  if (h < 0)
    h = 24 + h;

  return [h, m]
}

// Private func
function generatePlot() {
  const nmbSuspects = 4;

  let allRoom = getRandomElements(Object.keys(rooms), nmbSuspects + 1);

  // Build all data for the death type, time and who
  const deathRoom = allRoom[0];
  const deathTime = randomTime();

  const death = {
    "type": getRandomElements(deaths, 1), // How it was killed
    "motive": getRandomElements(murder_motives, 1), // Why
    "profession": getRandomElements(professions, 1), // Who
    "room": deathRoom, // Where
    "at": deathTime[0] + ":" + deathTime[1], // When
  };

  // Generate random data for the suspects
  allRoom = allRoom.slice(1, 1 + nmbSuspects);
  const suspectsProf = getRandomElements(forge_prefessions, 1).concat(getRandomElements(professions, nmbSuspects - 1));
  const names = "ABCDEFGHIJ";

  // Register all suspects with their name and alibi
  let suspects = {};
  for (let i = 0; i < nmbSuspects; ++i) {
    const name = names[i];

    const timeAlibiStart = addTime(deathTime[0], deathTime[1], -(15 + Math.floor(Math.random() * 40)));
    const timeAlibiEnd = addTime(deathTime[0], deathTime[1], (15 + Math.floor(Math.random() * 40)));

    suspects[name] = {
      alibi: {
        "room": allRoom[i],
        "from": timeAlibiStart[0] + ":" + timeAlibiStart[1],
        "to": timeAlibiEnd[0] + ":" + timeAlibiEnd[1],
      },
      prefession: suspectsProf[i],
    };
  }

  // Register observations to all suspects
  allRoom[0] = deathRoom; // A is the murderer

  for (let i = 0; i < nmbSuspects; ++i) {
    const name = names[i];

    const timeObsStart = addTime(deathTime[0], deathTime[1], -(5 + Math.floor(Math.random() * 10)));
    const timeObsEnd = addTime(deathTime[0], deathTime[1], (5 + Math.floor(Math.random() * 10)));

    suspects[name].obs = [{
      "room": allRoom[nmbSuspects - i - 1],
      "who": names[nmbSuspects - i - 1],
      "from": timeObsStart[0] + ":" + timeObsStart[1],
      "to": timeObsEnd[0] + ":" + timeObsEnd[1],
    }];
  }

  return {
    suspects: suspects,
    victim: death,
    murderer: "A"
  }
}

async function generateEndSpeech() {
  backend.end_speech = (await chatAIPrompt(createWatson(backend.plot))).text;
}

async function watsonHasFound() {
  return new Promise((resolve) => {
      const pl = window.pl;
      const session = pl.create();

      const rules = `liar(Person) :-
          alibi(Person, Room1),
          observed(Person, Room2),
          Room1 \\= Room2.
      `;

      // We add all the facts observed by Watson
      let facts = "";
      backend.watson.alibis.forEach(a => {
        facts += `alibi(${a.person}, ${a.room}).\n`;
      });
      backend.watson.observations.forEach(o => {
        facts += `observed(${o.person}, ${o.room}).\n`;
      });

      const program = facts + "\n\n" + rules;

      session.consult(program, {
        success: function () {
          session.query("liar(Person).", {
            success: function () {
              session.answer(answer => {
                resolve((answer && "links" in answer));
              });
            },
            error: function (err) { console.log("Query", err); }
          });
        },
        error: function (err) { console.log("Consult", err); }
      });
 });
}

async function generateGame() {
  console.log("Generate plot...");
  const plot = generatePlot();

  const res = await chatAIPrompt(createPlot(plot));

  backend.plot = res;
}