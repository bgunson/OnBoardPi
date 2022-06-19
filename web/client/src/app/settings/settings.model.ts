
export interface Settings {
    vehicle: Vehicle;
    connection: Connection
}

export interface Vehicle {
    make: string | null;
    model: string | null;
    year: number | null;
    vin: string | null;
}

export interface Connection {
    auto: boolean;
    parameters: {
        delay_cmds: number;
        portstr: string | null;
        baudrate: number | null;
        protocol: string | null;
    },
    log_level: string; 
    supported_only: boolean;
}