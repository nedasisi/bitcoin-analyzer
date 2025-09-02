"""
Module pour analyser les bottoms en batch avec cache persistant
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
        """Sauvegarde le cache"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)
    
    def get_cache_key(self, timestamp):
        """Génère une clé de cache pour un timestamp"""
        if isinstance(timestamp, pd.Timestamp):
            return timestamp.isoformat()
        return str(timestamp)
    
    def analyze_batch(self, bottoms_df, batch_size=20, delay=1.0, progress_callback=None):
        """
        Analyse un batch de bottoms avec gestion du cache
        
        Args:
            bottoms_df: DataFrame avec les bottoms
            batch_size: Taille des batches
            delay: Délai entre requêtes (secondes)
            progress_callback: Fonction callback(processed, total, message)
        
        Returns:
            results_df: DataFrame avec les résultats
            errors: Liste des erreurs
        """
        results = []
        errors = []
        total = len(bottoms_df)
        processed = 0
        
        for idx, row in bottoms_df.iterrows():
            cache_key = self.get_cache_key(idx)
            
            # Vérifier le cache
            if cache_key in self.cache:
                results.append(self.cache[cache_key])
                processed += 1
                if progress_callback:
                    progress_callback(processed, total, f"Chargé depuis cache: {idx}")
                continue
            
            # Analyser le bottom
            try:
                # Passer le prix si disponible
                kwargs = {}
                if 'price' in row:
                    kwargs['price'] = row['price']
                
                result = self.finder.get_exact_bottom_time(
                    bottom_time=idx,
                    **kwargs
                )
                
                if result:
                    # Ajouter le timestamp original
                    result['timestamp'] = idx
                    results.append(result)
                    
                    # Mettre en cache
                    self.cache[cache_key] = result
                    
                    # Sauvegarder périodiquement
                    if processed % 10 == 0:
                        self.save_cache()
                else:
                    errors.append({
                        'timestamp': idx,
                        'error': 'No data returned'
                    })
                
            except Exception as e:
                errors.append({
                    'timestamp': idx,
                    'error': str(e)
                })
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total, f"Analysé: {idx}")
            
            # Pause entre requêtes
            if processed < total:
                time.sleep(delay)
        
        # Sauvegarder le cache final
        self.save_cache()
        
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
            # Taille du cache
            cache_str = json.dumps(self.cache)
            stats['cache_size_kb'] = len(cache_str.encode()) / 1024
            
            # Dates
            timestamps = list(self.cache.keys())
            stats['oldest_entry'] = min(timestamps)
            stats['newest_entry'] = max(timestamps)
        
        return stats
    
    def clear_cache(self):
        """Efface le cache"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
    
    def export_to_csv(self, filename='data/exact_times_export.csv'):
        """Exporte le cache vers CSV"""
        if self.cache:
            df = pd.DataFrame.from_dict(self.cache, orient='index')
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            df.to_csv(filename)
            return filename
        return None