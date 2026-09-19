import axios from 'axios';
import { PlayerStats } from '../types';

const SOFASCORE_API_URL = 'https://api.sofascore.com/v1/'; // URL base de la API de Sofascore

export const fetchPlayerStats = async (playerId: number): Promise<PlayerStats> => {
    try {
        const response = await axios.get(`${SOFASCORE_API_URL}players/${playerId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching player stats for player ID ${playerId}:`, error);
        throw error;
    }
};

export const fetchMatchData = async (matchId: number) => {
    try {
        const response = await axios.get(`${SOFASCORE_API_URL}matches/${matchId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching match data for match ID ${matchId}:`, error);
        throw error;
    }
};

// Otras funciones para manejar datos de Sofascore pueden ser añadidas aquí.