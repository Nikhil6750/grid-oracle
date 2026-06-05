const JOLPI_BASE = 'https://api.jolpi.ca/ergast/f1';
const SEASON = '2026';

const COUNTRY_FLAGS = {
  Australia: '🇦🇺', China: '🇨🇳', Japan: '🇯🇵', USA: '🇺🇸',
  Canada: '🇨🇦', Monaco: '🇲🇨', Spain: '🇪🇸', Austria: '🇦🇹',
  UK: '🇬🇧', Belgium: '🇧🇪', Netherlands: '🇳🇱', Hungary: '🇭🇺',
  Italy: '🇮🇹', Azerbaijan: '🇦🇿', Singapore: '🇸🇬', Mexico: '🇲🇽',
  Brazil: '🇧🇷', Qatar: '🇶🇦', UAE: '🇦🇪'
};

const CIRCUIT_NAMES = {
  albert_park: 'Albert Park', shanghai: 'Shanghai',
  suzuka: 'Suzuka', miami: 'Miami Autodrome',
  villeneuve: 'Circuit Gilles Villeneuve', monaco: 'Circuit de Monaco',
  catalunya: 'Circuit de Barcelona-Catalunya', red_bull_ring: 'Red Bull Ring',
  silverstone: 'Silverstone', spa: 'Spa-Francorchamps',
  hungaroring: 'Hungaroring', zandvoort: 'Zandvoort',
  monza: 'Autodromo Nazionale di Monza', madring: 'Madring Madrid',
  baku: 'Baku City Circuit', marina_bay: 'Marina Bay Street Circuit',
  americas: 'Circuit of the Americas', rodriguez: 'Autodromo Hermanos Rodriguez',
  interlagos: 'Interlagos', vegas: 'Las Vegas Strip Circuit',
  losail: 'Losail International Circuit', yas_marina: 'Yas Marina Circuit'
};

const LAPS = {
  albert_park: 58, shanghai: 56, suzuka: 53, miami: 57,
  villeneuve: 70, monaco: 78, catalunya: 66, red_bull_ring: 71,
  silverstone: 52, spa: 44, hungaroring: 70, zandvoort: 72,
  monza: 53, madring: 55, baku: 51, marina_bay: 62,
  americas: 56, rodriguez: 71, interlagos: 71, vegas: 50,
  losail: 57, yas_marina: 58
};

const DISTANCES = {
  albert_park: 307.574, shanghai: 305.066, suzuka: 307.471, miami: 308.326,
  villeneuve: 305.270, monaco: 260.286, catalunya: 307.236, red_bull_ring: 306.452,
  silverstone: 306.198, spa: 308.052, hungaroring: 306.63, zandvoort: 308.586,
  monza: 306.72, madring: 306.87, baku: 306.049, marina_bay: 308.706,
  americas: 308.405, rodriguez: 305.354, interlagos: 305.879, vegas: 309.958,
  losail: 308.611, yas_marina: 306.183
};

export async function getFullSeasonSchedule() {
  const res = await fetch(`${JOLPI_BASE}/${SEASON}.json`);
  const data = await res.json();
  return data.MRData.RaceTable.Races;
}

export async function getNextRace() {
  const res = await fetch(`${JOLPI_BASE}/${SEASON}/next.json`);
  const data = await res.json();
  const race = data.MRData.RaceTable.Races[0];
  if (!race) return null;
  const circuitId = race.Circuit?.circuitId || '';
  return {
    round: parseInt(race.round),
    name: race.raceName,
    circuitId,
    circuitName: CIRCUIT_NAMES[circuitId] || race.Circuit?.circuitName,
    locality: race.Circuit?.Location?.locality,
    country: race.Circuit?.Location?.country,
    flag: COUNTRY_FLAGS[race.Circuit?.Location?.country] || '🏁',
    raceDate: race.date,
    raceTime: race.time,
    raceDateTime: new Date(`${race.date}T${race.time}`),
    qualifyingDate: race.Qualifying?.date,
    qualifyingTime: race.Qualifying?.time,
    fp1Date: race.FirstPractice?.date,
    isSprint: !!race.Sprint,
    laps: LAPS[circuitId] || 57,
    distance: DISTANCES[circuitId] || 305,
  };
}

export async function getLastRaceResult() {
  const res = await fetch(`${JOLPI_BASE}/${SEASON}/last/results.json`);
  const data = await res.json();
  const race = data.MRData.RaceTable.Races[0];
  if (!race) return null;
  return {
    raceName: race.raceName,
    circuitName: race.Circuit?.circuitName,
    round: parseInt(race.round),
    results: race.Results?.slice(0, 3).map(r => ({
      position: r.position,
      name: `${r.Driver.givenName.charAt(0)}. ${r.Driver.familyName}`,
      team: r.Constructor.name,
      time: r.Time?.time || r.status,
      points: r.points,
      number: r.number,
    })) || []
  };
}

export async function getDriverStandings() {
  const res = await fetch(`${JOLPI_BASE}/${SEASON}/driverStandings.json`);
  const data = await res.json();
  return data.MRData.StandingsTable.StandingsLists[0]?.DriverStandings || [];
}

export { COUNTRY_FLAGS, CIRCUIT_NAMES };
