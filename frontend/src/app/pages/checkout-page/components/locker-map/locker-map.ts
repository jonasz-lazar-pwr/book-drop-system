import {
  Component,
  Input,
  Output,
  EventEmitter,
  AfterViewInit,
  OnChanges,
  SimpleChanges,
  ViewChild,
  ElementRef,
} from '@angular/core';
import maplibregl from 'maplibre-gl';
import { LockerResponse } from '@models/checkout';

@Component({
  selector: 'app-locker-map',
  imports: [],
  templateUrl: './locker-map.html',
  styleUrls: ['./locker-map.scss'],
})
export class LockerMap implements AfterViewInit, OnChanges {
  @Input() lockers: LockerResponse[] = [];
  @Input() selectedLockerId: string | null = null;
  @Output() lockerSelected = new EventEmitter<LockerResponse>();
  @ViewChild('mapContainer') mapContainer!: ElementRef<HTMLDivElement>;

  private map?: maplibregl.Map;
  private markerMap = new Map<string, maplibregl.Marker>();

  ngAfterViewInit() {
    if (this.map) return;

    this.map = new maplibregl.Map({
      container: this.mapContainer.nativeElement,
      style: 'https://tiles.stadiamaps.com/styles/alidade_smooth.json',
      center: [17.0385, 51.1079],
      zoom: 13,
    });

    this.map.on('load', () => {
      if (this.lockers.length) this.renderMarkers();
    });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['lockers'] && this.map) {
      this.renderMarkers();
    }
    if (changes['selectedLockerId'] && this.map) {
      this.highlightMarker(this.selectedLockerId);
    }
  }

  private renderMarkers() {
    // Remove old markers before re-rendering
    this.markerMap.forEach((m) => m.remove());
    this.markerMap.clear();

    if (!this.map || !this.lockers.length) return;

    for (const l of this.lockers) {
      const marker = new maplibregl.Marker({ color: '#004E89' })
        .setLngLat([l.lon, l.lat])
        .addTo(this.map);

      marker.getElement().addEventListener('click', () => {
        this.lockerSelected.emit(l);
        this.highlightMarker(l.id);
      });

      this.markerMap.set(l.id, marker);
    }

    const bounds = new maplibregl.LngLatBounds();
    this.lockers.forEach((l) => bounds.extend([l.lon, l.lat]));
    this.map.fitBounds(bounds, { padding: 40 });
  }

  private highlightMarker(id: string | null) {
    // Visually highlight the selected marker
    this.markerMap.forEach((marker, markerId) => {
      const isActive = markerId === id;
      const color = isActive ? '#0074D9' : '#004E89';

      const pos = marker.getLngLat();
      marker.remove();
      const newMarker = new maplibregl.Marker({ color })
        .setLngLat(pos)
        .addTo(this.map!);

      newMarker.getElement().addEventListener('click', () => {
        const locker = this.lockers.find((l) => l.id === markerId);
        if (locker) this.lockerSelected.emit(locker);
      });

      this.markerMap.set(markerId, newMarker);

      if (isActive) {
        this.map?.flyTo({
          center: pos,
          zoom: 15,
          essential: true,
        });
      }
    });
  }
}
