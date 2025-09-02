"""
Module pour analyser tous les bottoms historiques par batch
avec sauvegarde progressive et reprise après interruption
"""

import pandas as pd
import json
import os
from datetime import datetime
import time
from exact_bottom_finder import ExactBottomFinder

class BatchExactTimeAnalyzer:
    def __init__(self, cache_dir='data/exact_times'):
        """
        Initialise l'analyseur batch avec cache persistant
        """
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'exact_times_cache.json')
        self.progress_file = os.path.join(cache_dir, 'analysis_progress.json')
        
        # Créer le dossier cache si nécessaire
        os.makedirs(cache_dir, exist_ok=True)
        
        # Charger le cache existant
        self.cache = self.load_cache()
        self.finder = ExactBottomFinder()
    
    def load_cache(self):
        """Charge le cache des heures exactes déjà calculées"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """Sauvegarde le cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2, default=str)
    
    def get_cache_key(self, timestamp):
        """Génère une clé unique pour le cache"""
        if hasattr(timestamp, 'strftime'):
            return timestamp.strftime('%Y-%m-%d_%H-%M-%S')
        return str(timestamp)
    
    def analyze_batch(self, bottoms_df, batch_size=10, delay=1.0, progress_callback=None):
        """
        Analyse les bottoms par batch avec sauvegarde progressive
        
        Args:
            bottoms_df: DataFrame des bottoms à analyser
            batch_size: Nombre de bottoms par batch
            delay: Délai entre chaque appel API (secondes)
            progress_callback: Fonction pour mettre à jour la progression
        
        Returns:
            DataFrame avec les heures exactes
        """
        results = []
        errors = []
        total = len(bottoms_df)
        processed = 0
        
        # Diviser en batches
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = bottoms_df.iloc[batch_start:batch_end]
            
            for idx, row in batch.iterrows():
                cache_key = self.get_cache_key(idx)
                
                # Vérifier si déjà dans le cache
                if cache_key in self.cache:
                    results.append(self.cache[cache_key])
                    processed += 1
                    if progress_callback:
                        progress_callback(processed, total, f"Chargé depuis cache: {idx.strftime('%Y-%m-%d')}")
                    continue
                
                try:
                    # Convertir en UTC pour l'API
                    idx_utc = idx
                    if hasattr(idx, 'tz_convert'):
                        if idx.tz:
                            idx_utc = idx.tz_convert('UTC').tz_localize(None)
                    
                    # Récupérer l'heure exacte
                    exact_data = self.finder.get_exact_bottom_time(
                        approximate_time=idx_utc,
                        symbol='BTC/USDT:USDT',
                        window_hours=4
                    )
                    
                    if exact_data:
                        result = {
                            'timestamp': idx,
                            'exact_time': exact_data['exact_time'],
                            'exact_price': exact_data['exact_price'],
                            'volume_at_bottom': exact_data['volume_at_bottom'],
                            'precision': exact_data['precision'],
                            'original_price': row['price']
                        }
                        
                        # Ajouter au cache
                        self.cache[cache_key] = result
                        results.append(result)
                        
                        # Sauvegarder le cache après chaque succès
                        if processed % 5 == 0:  # Sauvegarder tous les 5 bottoms
                            self.save_cache()
                    else:
                        errors.append({'timestamp': idx, 'error': 'No data returned'})
                    
                    processed += 1
                    
                    if progress_callback:
                        progress_callback(processed, total, f"Analysé: {idx.strftime('%Y-%m-%d')}")
                    
                    # Pause entre les requêtes
                    time.sleep(delay)
                    
                except Exception as e:
                    errors.append({'timestamp': idx, 'error': str(e)})
                    processed += 1
                    if progress_callback:
                        progress_callback(processed, total, f"Erreur: {idx.strftime('%Y-%m-%d')}")
            
            # Sauvegarder après chaque batch
            self.save_cache()
            
            # Pause plus longue entre les batches
            if batch_end < total:
                time.sleep(delay * 2)
        
        # Sauvegarder final
        self.save_cache()
        
        return pd.DataFrame(results), errors
    
    def get_statistics(self):
        """Retourne les statistiques du cache"""
        return {
            'total_cached': len(self.cache),
            'cache_size_kb': os.path.getsize(self.cache_file) / 1024 if os.path.exists(self.cache_file) else 0,
            'oldest_entry': min(self.cache.keys()) if self.cache else None,
            'newest_entry': max(self.cache.keys()) if self.cache else None
        }
    
    def clear_cache(self):
        """Efface le cache"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        return True
    
    def export_to_csv(self, output_file='exact_times_full.csv'):
        """Exporte tout le cache en CSV"""
        if not self.cache:
            return None
        
        df = pd.DataFrame.from_dict(self.cache, orient='index')
        df.to_csv(output_file)
        return output_file