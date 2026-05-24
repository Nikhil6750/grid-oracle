export const API_BASE_URL = 'http://127.0.0.1:8000';

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    return res.ok;
  } catch (error) {
    return false;
  }
}

export async function getRacePrediction({ season, round, stage }) {
  const url = new URL(`${API_BASE_URL}/predict/race`);
  url.searchParams.append('season', season);
  url.searchParams.append('round', round);
  url.searchParams.append('stage', stage);
  
  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`Error fetching prediction: ${res.statusText}`);
  }
  return await res.json();
}

export async function getLiveRaceResults(season = 'current', round = 'last') {
  try {
    const res = await fetch(`https://api.jolpi.ca/ergast/f1/${season}/${round}/results.json`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.MRData.RaceTable.Races[0]; // Returns the race object containing Results array
  } catch (error) {
    return null;
  }
}
