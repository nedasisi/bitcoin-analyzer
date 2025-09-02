"""
Module pour analyser les bottoms en batch avec cache persistant
Version simplifiée sans problèmes de sérialisation JSON
"""

import pandas as pd
import json
import os
from datetime import datetime
import time
from exact_bottom_finder import ExactBottomFinder

class BatchExactTimeAnalyzer:
    def __init__(self, cache_file='data/exact_times_cache.json'):
        """Initialise l'analyseur avec cache"""
        self.cache_file = cache_file
        self.finder = ExactBottomFinder()
        self.cache = self.load_cache()
        
    def load_cache(self):
        """Charge le cache depuis le fichier"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """Sauvegarde le cache - version simplifiée qui convertit tout en string"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            # Convertir tout le cache en format sérialisable
            serializable_cache = {}
            for key, value in self.cache.items():
                # Convertir la clé en string
                str_key = str(key)
                
                # Convertir la valeur
                if isinstance(value, dict):
                    serializable_value = {}
                    for k, v in value.items():
                        # Convertir chaque valeur en string ou type de base
                        if hasattr(v, 'isoformat'):
                            serializable_value[k] = v.isoformat()
                        elif pd.isna(v) or v is None:
                            serializable_value[k] = None
                        else:
                            serializable_value[k] = str(v)
                    serializable_cache[str_key] = serializable_value
                else:
                    serializable_cache[str_key] = str(value)
            
            # Sauvegarder
            with open(self.cache_file, 'w') as f:
                json.dump(serializable_cache, f, indent=2)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du cache: {e}")
    
    def get_cache_key(self, timestamp):
        """Génère une clé de cache pour un timestamp"""
        if hasattr(timestamp, 'isoformat'):
            return timestamp.isoformat()
        return str(timestamp)
    
    def analyze_batch(self, bottoms_df, batch_size=20, delay=1.0, progress_callback=None):
        """
        Analyse un batch de bottoms avec gestion du cache
        Version simplifiée qui évite les problèmes de sérialisation
        """
        results = []
        errors = []
        total = len(bottoms_df)
        processed = 0
        
        for idx, row in bottoms_df.iterrows():
            cache_key = self.get_cache_key(idx)
            
            # Vérifier le cache
            if cache_key in self.cache:
                # Utiliser les données du cache
                cached = self.cache[cache_key]
                # Reconstruire le résultat
                result = {
                    'timestamp': idx,
                    'exact_time': cached.get('exact_time', idx),
                    'exact_price': float(cached.get('exact_price', 0)) if cached.get('exact_price') else 0,
                    'original_price': float(cached.get('original_price', 0)) if cached.get('original_price') else 0,
                    'time_difference_minutes': float(cached.get('time_difference_minutes', 0)) if cached.get('time_difference_minutes') else 0,
                    'volume_at_bottom': float(cached.get('volume_at_bottom', 0)) if cached.get('volume_at_bottom') else 0,
                    'data_points': int(cached.get('data_points', 0)) if cached.get('data_points') else 0,
                    'note': cached.get('note', '')
                }
                results.append(result)
                processed += 1
                if progress_callback:
                    progress_callback(processed, total, f"Chargé depuis cache: {idx}")
                continue
            
            # Analyser le bottom
            try:
                # Passer le prix si disponible
                kwargs = {}
                if 'price' in row:
                    kwargs['price'] = float(row['price'])
                
                result = self.finder.get_exact_bottom_time(
                    bottom_time=idx,
                    **kwargs
                )
                
                if result:
                    # Ajouter le timestamp original
                    result['timestamp'] = idx
                    results.append(result)
                    
                    # Créer une version sérialisable pour le cache
                    cache_entry = {
                        'exact_time': str(result.get('exact_time', '')),
                        'exact_price': float(result.get('exact_price', 0)),
                        'original_price': float(result.get('original_price', 0)),
                        'time_difference_minutes': float(result.get('time_difference_minutes', 0)),
                        'volume_at_bottom': float(result.get('volume_at_bottom', 0)),
                        'data_points': int(result.get('data_points', 0)),
                        'note': str(result.get('note', ''))
                    }
                    self.cache[cache_key] = cache_entry
                    
                    # Sauvegarder périodiquement
                    if processed % 10 == 0:
                        self.save_cache()
                else:
                    errors.append({
                        'timestamp': str(idx),
                        'error': 'No data returned'
                    })
                
            except Exception as e:
                print(f"Erreur lors de l'analyse de {idx}: {e}")
                errors.append({
                    'timestamp': str(idx),
                    'error': str(e)
                })
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total, f"Analysé: {idx}")
            
            # Pause entre requêtes
            if processed < total:
                time.sleep(delay)
        
        # Sauvegarder le cache final
        try:
            self.save_cache()
        except Exception as e:
            print(f"Erreur lors de la sauvegarde finale du cache: {e}")
        
        # Créer DataFrame des résultats
        if results:
            results_df = pd.DataFrame(results)
            return results_df, errors
        
        return pd.DataFrame(), errors
    
    def get_statistics(self):
        """Retourne les statistiques du cache"""
        stats = {
            'total_cached': len(self.cache),
            'cache_size_kb': 0,
            'oldest_entry': None,
            'newest_entry': None
        }
        
        if self.cache:
            try:
                # Taille approximative
                cache_str = str(self.cache)
                stats['cache_size_kb'] = len(cache_str.encode()) / 1024
                
                # Dates
                timestamps = list(self.cache.keys())
                if timestamps:
                    stats['oldest_entry'] = min(timestamps)
                    stats['newest_entry'] = max(timestamps)
            except:
                pass
        
        return stats
    
    def clear_cache(self):
        """Efface le cache"""
        self.cache = {}
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except Exception as e:
            print(f"Erreur lors de la suppression du cache: {e}")
    
    def export_to_csv(self, filename='data/exact_times_export.csv'):
        """Exporte le cache vers CSV"""
        if self.cache:
            try:
                # Créer une liste de dictionnaires pour le DataFrame
                data = []
                for key, value in self.cache.items():
                    row = {'cache_key': key}
                    row.update(value)
                    data.append(row)
                
                df = pd.DataFrame(data)
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                df.to_csv(filename, index=False)
                return filename
            except Exception as e:
                print(f"Erreur lors de l'export CSV: {e}")
                return None
        return None