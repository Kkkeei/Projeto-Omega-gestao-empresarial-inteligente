import {apiFetch} from './client';
import type {Usuario} from '../../auth/AuthContext';
export const meuUsuario=()=>apiFetch<Usuario>('/api/v1/auth/me');
