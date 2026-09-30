import {apiFetch} from './client'; import type {DashboardResumo} from '../../types'; export const buscarResumoDashboard=()=>apiFetch<DashboardResumo>('/api/v1/dashboard/resumo');
